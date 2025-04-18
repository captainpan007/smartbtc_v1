# core/executor.py
import pandas as pd
from ta.volatility import AverageTrueRange
from core.config_loader import load_config

class TradeExecutor:
    def __init__(self, config, simulate=False, df=None):
        self.simulate = simulate
        self.df = df # 用于计算动态滑点的数据
        binance_cfg = config.get("binance", {})
        trading_cfg = config.get("trading", {})

        # 凭证 (如果 simulate=False, 则需要用于真实交易)
        self.api_key = binance_cfg.get("api_key")
        self.api_secret = binance_cfg.get("api_secret")

        # 费率和滑点
        self.commission_rate = binance_cfg.get("commission_rate", 0.00075)
        self.base_slippage_rate = trading_cfg.get("slippage_base_rate", 0.0005)

        # --- 持仓状态 (模拟交易时由 Executor 维护) ---
        self.holdings_base_currency = 0.0 # 持有的基础货币数量 (e.g., BTC)
        self.average_entry_price = 0.0 # 平均持仓成本
        # 注意：在真实交易中，持仓状态应主要从交易所查询获取

    def update_data(self, df):
        """允许外部更新用于计算滑点的数据"""
        self.df = df

    def calculate_dynamic_slippage(self, price):
        """计算动态滑点 (基于 ATR)"""
        if self.df is None or self.df.empty:
            # print("[Exec] WARN: No data for dynamic slippage, using base rate.")
            return price * self.base_slippage_rate

        try:
            atr = AverageTrueRange(high=self.df['high'], low=self.df['low'], close=self.df['close'], window=14).average_true_range()
            latest_atr = atr.iloc[-1]

            if pd.isna(latest_atr) or price <= 0:
                 # print("[Exec] WARN: Invalid ATR or price for slippage calc, using base rate.")
                 return price * self.base_slippage_rate

            atr_ratio = latest_atr / price

            # 示例性调整逻辑，可根据回测优化
            if atr_ratio > 0.02: # 波动剧烈时，滑点加倍
                slippage_rate = self.base_slippage_rate * 2
            elif atr_ratio < 0.005: # 波动平缓时，滑点减半
                slippage_rate = self.base_slippage_rate * 0.5
            else:
                slippage_rate = self.base_slippage_rate
            return price * slippage_rate

        except Exception as e:
             print(f"[Exec] ERROR: Calculating slippage failed: {e}. Using base rate.")
             return price * self.base_slippage_rate

    def execute(self, order):
        """执行订单 (模拟或真实)"""
        if self.simulate:
            return self._simulate_order(order)
        else:
            return self._real_order(order)

    def _simulate_order(self, order):
        """模拟订单执行，并计算盈亏"""
        action = order["action"]
        signal_price = order["price"] # 信号触发时的价格
        amount_base_currency = order["amount"] # 要交易的基础货币数量 (e.g., BTC)
        symbol = order["symbol"]
        timestamp = order["timestamp"]

        if action == "buy":
            # --- 处理买入 ---
            if amount_base_currency <= 0:
                print(f"[Sim] INFO: Buy amount is zero or negative, skipping.")
                return None

            slippage = self.calculate_dynamic_slippage(signal_price)
            execution_price = signal_price + slippage # 买入价更高
            commission = amount_base_currency * execution_price * self.commission_rate

            # 更新持仓均价和数量
            new_total_cost = (self.average_entry_price * self.holdings_base_currency) + (execution_price * amount_base_currency)
            self.holdings_base_currency += amount_base_currency
            if self.holdings_base_currency > 0:
                 self.average_entry_price = new_total_cost / self.holdings_base_currency
            else: # 避免除零错误 (理论上买入后不会为0)
                 self.average_entry_price = 0.0

            print(f"[Sim] {timestamp} BUY {amount_base_currency:.6f} {symbol} @ Execution Price: {execution_price:.2f} (Signal: {signal_price:.2f}, Slippage: {slippage:.4f}, Commission: {commission:.4f}). New Holdings: {self.holdings_base_currency:.6f}, Avg Price: {self.average_entry_price:.2f}")

            return {
                "symbol": symbol, "action": "buy", "price": execution_price,
                "amount": amount_base_currency, "commission": commission,
                "slippage": slippage, "pnl": 0.0, # 买入时不计算 PnL
                "timestamp": timestamp, "holdings": self.holdings_base_currency,
                 "avg_entry_price": self.average_entry_price
            }

        elif action == "sell":
            # --- 处理卖出 ---
            if self.holdings_base_currency <= 0:
                print(f"[Sim] INFO: No holdings to sell {symbol}.")
                return None

            # 确保卖出数量不超过持仓量
            sell_amount = min(amount_base_currency, self.holdings_base_currency)
            if sell_amount <= 0:
                 print(f"[Sim] INFO: Sell amount is zero or negative, skipping.")
                 return None

            slippage = self.calculate_dynamic_slippage(signal_price)
            execution_price = signal_price - slippage # 卖出价更低
            commission = sell_amount * execution_price * self.commission_rate

            # 计算此部分卖出的盈亏
            # PnL = (卖出价 - 平均买入价) * 卖出数量 - 卖出手续费
            # (注意: 买入手续费已隐含在平均买入价的计算中，或在更新余额时考虑)
            pnl = (execution_price - self.average_entry_price) * sell_amount - commission

            # 更新持仓
            self.holdings_base_currency -= sell_amount

            print(f"[Sim] {timestamp} SELL {sell_amount:.6f} {symbol} @ Execution Price: {execution_price:.2f} (Signal: {signal_price:.2f}, Slippage: {slippage:.4f}, Commission: {commission:.4f}). PnL: {pnl:.2f}. Remaining Holdings: {self.holdings_base_currency:.6f}")

            # 如果全部卖出，重置平均成本
            if self.holdings_base_currency < 1e-9: # 考虑浮点数精度
                self.average_entry_price = 0.0
                self.holdings_base_currency = 0.0 # 显式置零

            return {
                "symbol": symbol, "action": "sell", "price": execution_price,
                "amount": sell_amount, "commission": commission,
                "slippage": slippage, "pnl": pnl, # 本次卖出的 PnL
                "timestamp": timestamp, "holdings": self.holdings_base_currency,
                "avg_entry_price": self.average_entry_price if self.holdings_base_currency > 0 else 0.0
            }
        else:
            print(f"[Sim] WARN: Unknown action '{action}'")
            return None

    def _real_order(self, order):
        """
        执行真实订单 - 需要您根据 ccxt 和币安 API 实现
        """
        action = order["action"]
        signal_price = order["price"] # 信号触发时的价格
        amount_base_currency = order["amount"] # 要交易的基础货币数量
        symbol = order["symbol"]
        timestamp = order["timestamp"]
        # stop_loss_price = order.get("stop_loss") # 从订单获取止损价
        # take_profit_price = order.get("take_profit") # 从订单获取止盈价

        print(f"[Real] Received order: {action} {amount_base_currency} {symbol} at signal price {signal_price}")
        print(f"[Real] --- Placeholder for actual Binance API call using ccxt ---")

        # 1. 初始化 ccxt 客户端
        # exchange = ccxt.binance({
        #     'apiKey': self.api_key,
        #     'secret': self.api_secret,
        #     # 'options': {'defaultType': 'spot'} # 或 'future'/'margin'
        # })
        # try:
        #     exchange.load_markets()
        # except ccxt.AuthenticationError:
        #      print("[Real] ERROR: Binance authentication failed. Check API keys.")
        #      return None
        # except Exception as e:
        #      print(f"[Real] ERROR: Failed to connect to Binance: {e}")
        #      return None


        # 2. 获取账户余额和当前持仓 (用于验证和计算)
        # balance = exchange.fetch_balance()
        # available_quote = balance['free'][symbol.split('/')[1]] # e.g., USDT
        # current_holdings = balance['free'][symbol.split('/')[0]] # e.g., BTC

        # 3. 验证交易 (资金、持仓等) - 结合 RiskManager
        # if action == 'buy' and available_quote < amount_base_currency * signal_price: # 粗略估算
        #     print("[Real] ERROR: Insufficient funds.")
        #     return None
        # if action == 'sell' and current_holdings < amount_base_currency:
        #      print("[Real] ERROR: Insufficient holdings.")
        #      return None


        # 4. 创建订单 (市价单或限价单)
        #    - 市价单风险：滑点不可控
        #    - 限价单风险：可能不成交或部分成交
        # order_type = 'limit' # 或 'market'
        # order_side = 'buy' if action == 'buy' else 'sell'
        # price_for_order = signal_price # 对于限价单，需要考虑滑点或设置一个略优的价格

        # print(f"[Real] Attempting to place {order_type} {order_side} order for {amount_base_currency} {symbol}...")
        # try:
        #     placed_order = exchange.create_order(
        #         symbol=symbol,
        #         type=order_type,
        #         side=order_side,
        #         amount=amount_base_currency
        #         # price=price_for_order # 仅限价单需要
        #         # params={'stopPrice': stop_loss_price, 'type': 'STOP_MARKET'} # OCO 或止损单需要额外参数
        #     )
        #     print(f"[Real] Order placed successfully: {placed_order['id']}")
        #     # TODO: 后续需要跟踪订单状态，获取实际成交价格、手续费，并计算 PnL
        #     #       这通常需要轮询订单状态或使用 WebSocket
        #     #       需要记录成交信息以更新模拟状态或数据库
        #     return { # 返回一个初步的、基于尝试下单的信息
        #          "symbol": symbol, "action": action, "price": signal_price, # 信号价，非成交价
        #          "amount": amount_base_currency, "commission": None, # 未知
        #          "slippage": None, # 未知
        #          "pnl": None, # 未知
        #          "timestamp": timestamp, "order_id": placed_order['id'], "status": "submitted"
        #     }

        # except ccxt.InsufficientFunds as e:
        #     print(f"[Real] ERROR: Insufficient funds on exchange: {e}")
        #     return None
        # except ccxt.OrderNotFound as e:
        #     # 如果是尝试取消订单等操作
        #     print(f"[Real] ERROR: Order not found: {e}")
        #     return None
        # except ccxt.NetworkError as e:
        #      print(f"[Real] ERROR: Network error communicating with Binance: {e}")
        #      return None
        # except ccxt.ExchangeError as e:
        #      print(f"[Real] ERROR: Binance exchange error: {e}")
        #      return None
        # except Exception as e:
        #      print(f"[Real] ERROR: An unexpected error occurred during order execution: {e}")
        #      return None

        # --- 模拟返回，表示未实现 ---
        return {
            "symbol": symbol, "action": action, "price": signal_price,
            "amount": amount_base_currency, "commission": 0, "slippage": 0, "pnl": 0,
            "timestamp": timestamp, "status": "real_execution_not_implemented"
        }

    def get_holdings(self):
         """获取当前模拟持仓量"""
         return self.holdings_base_currency

    def get_average_entry_price(self):
         """获取当前模拟持仓均价"""
         return self.average_entry_price