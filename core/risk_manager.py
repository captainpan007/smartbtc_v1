# core/risk_manager.py
import os
import pandas as pd
from ta.volatility import AverageTrueRange # 确保引入 ATR 计算库
from core.config_loader import load_config

class RiskManager:
    def __init__(self, config):
        risk_cfg = config.get("risk", {})
        trading_cfg = config.get("trading", {})

        self.initial_balance = risk_cfg.get("initial_balance", 10000.0)
        self.peak_balance = self.initial_balance
        self.current_balance = self.initial_balance

        self.sl_atr_multiplier = risk_cfg.get("sl_atr_multiplier", 2.0)
        self.tp_atr_multiplier = risk_cfg.get("tp_atr_multiplier", 3.0) # 新增止盈倍数
        self.max_drawdown_pct = risk_cfg.get("max_drawdown_pct", 0.20)
        self.max_position_risk_pct = risk_cfg.get("max_position_risk_pct", 0.02) # 单笔风险占总资金比例

        self.trading_paused = False
        self.pause_log = "logs/drawdown_monitor.log"
        os.makedirs(os.path.dirname(self.pause_log), exist_ok=True)

    def update_balance(self, pnl):
        """根据单笔交易盈亏更新余额"""
        self.current_balance += pnl
        self.peak_balance = max(self.peak_balance, self.current_balance)
        self._check_drawdown()

    def set_balance(self, new_balance):
        """直接设置余额（例如，回测开始时）"""
        self.current_balance = new_balance
        self.peak_balance = max(self.peak_balance, new_balance) # 重置峰值

    def _check_drawdown(self):
        """检查是否达到最大回撤"""
        if self.peak_balance <= 0: # 避免除零错误
             drawdown = 0
        else:
            drawdown = 1 - self.current_balance / self.peak_balance

        if drawdown > self.max_drawdown_pct:
            if not self.trading_paused:
                self.trading_paused = True
                log_msg = f"[{pd.Timestamp.now()}] [ALERT] Max drawdown exceeded! Drawdown: {drawdown:.2%}, Balance: {self.current_balance:.2f}. Trading paused.\n"
                print(log_msg.strip())
                with open(self.pause_log, "a") as f:
                    f.write(log_msg)
        # else:
            # 如果需要，可以添加自动恢复逻辑，但通常建议手动检查后恢复
            # if self.trading_paused:
            #     self.reset_trading_pause()

    def calculate_atr(self, df: pd.DataFrame, window=14) -> float:
        """计算最新的 ATR 值"""
        if df is None or len(df) < window + 1:
            print("[Risk] WARN: 数据不足，无法计算 ATR。返回 0。")
            return 0.0
        try:
            atr_series = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=window).average_true_range()
            latest_atr = atr_series.iloc[-1]
            return latest_atr if pd.notna(latest_atr) else 0.0
        except Exception as e:
            print(f"[Risk] ERROR: 计算 ATR 时出错: {e}")
            return 0.0

    def calculate_sl_tp_prices(self, entry_price: float, atr: float, action: str):
        """根据入场价、ATR和方向计算止损止盈价格"""
        if atr <= 0:
            print("[Risk] WARN: ATR <= 0, 无法计算止损止盈。")
            return None, None

        if action == "buy":
            stop_loss_price = entry_price - self.sl_atr_multiplier * atr
            take_profit_price = entry_price + self.tp_atr_multiplier * atr
        elif action == "sell": # 注意：这是做空的情况，您的代码目前似乎只做多
            stop_loss_price = entry_price + self.sl_atr_multiplier * atr
            take_profit_price = entry_price - self.tp_atr_multiplier * atr
        else:
            return None, None
        return stop_loss_price, take_profit_price

    def calculate_position_size(self, entry_price: float, stop_loss_price: float, symbol: str):
        """
        根据单笔最大风险比例、止损距离计算仓位大小（单位：基础货币，如 BTC）
        """
        if stop_loss_price is None or entry_price <= 0 or abs(entry_price - stop_loss_price) == 0:
            print("[Risk] WARN: 无法计算仓位大小 (价格或止损无效)。")
            return 0.0

        # 每单位基础货币的风险金额 (USDT)
        risk_per_unit = abs(entry_price - stop_loss_price)

        # 允许的总风险金额 (USDT)
        total_risk_amount = self.current_balance * self.max_position_risk_pct

        if risk_per_unit <= 0:
             print("[Risk] WARN: Risk per unit is zero, cannot calculate position size.")
             return 0.0

        # 计算仓位大小（基础货币数量，如 BTC）
        position_size_base_currency = total_risk_amount / risk_per_unit

        # TODO: 这里需要考虑币安对特定交易对的最小下单量和精度要求
        # 例如：BTCUSDT 可能要求最小下单量 0.0001 BTC
        # position_size_base_currency = self.adjust_for_min_order_size(position_size_base_currency, symbol)

        print(f"[Risk] Balance: {self.current_balance:.2f}, Risk Amount: {total_risk_amount:.2f}, Risk Per Unit: {risk_per_unit:.4f}, Calculated Size: {position_size_base_currency:.6f}")
        return round(position_size_base_currency, 6) # 假设保留6位小数，需根据实际调整

    # def adjust_for_min_order_size(self, size, symbol):
    #     # 示例：需要实现根据 symbol 获取币安最小下单量的逻辑
    #     min_size = get_min_order_size_from_binance(symbol) # 需要实现这个函数
    #     if size < min_size:
    #         print(f"[Risk] WARN: Calculated size {size} is less than min order size {min_size}. Returning 0.")
    #         return 0.0
    #     # 还需要考虑下单精度 stepSize
    #     step_size = get_step_size_from_binance(symbol) # 需要实现
    #     adjusted_size = floor(size / step_size) * step_size
    #     return adjusted_size

    def validate_trade(self, order_size_base_currency, entry_price):
        if self.trading_paused:
            print("[Risk] 🚫 交易暂停（达到最大回撤）。")
            return False

        # 增加资金检查 (粗略)
        required_quote_amount = order_size_base_currency * entry_price
        # 可以稍微宽松一点，比如检查是否大于可用余额的99%，为滑点和手续费留余地
        if required_quote_amount > self.current_balance * 0.99:
            print(f"[Risk] 🚫 资金不足 (预估)。需要: ~{required_quote_amount:.2f}, 可用: {self.current_balance:.2f}")
            return False

        # 可以添加其他验证...
        return True

    def reset_trading_pause(self):
        """手动重置交易暂停状态"""
        if self.trading_paused:
            self.trading_paused = False
            self.peak_balance = self.current_balance # 重置峰值以避免立即再次触发
            log_msg = f"[{pd.Timestamp.now()}] [INFO] Trading resumed manually. Peak balance reset to {self.peak_balance:.2f}\n"
            print(log_msg.strip())
            with open(self.pause_log, "a") as f:
                f.write(log_msg)