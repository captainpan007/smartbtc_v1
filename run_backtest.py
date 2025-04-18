# run_backtest.py
import pandas as pd
import time
import os
from core.data_loader import MarketDataLoader
# from core.market_state import MarketStateDetector # 信号生成器内部会用
from core.signal_generator import SignalGenerator
from core.executor import TradeExecutor
from core.risk_manager import RiskManager
from core.notifier import Notifier
from core.config_loader import load_config # 引入配置加载

def run_backtest(data_file, log_path, config):
    print(f"[Backtest] ⏳ Starting backtest with {data_file}...")

    # --- 初始化组件 ---
    trading_cfg = config.get("trading", {})
    symbol = trading_cfg.get("symbol", "BTC/USDT")
    timeframe = trading_cfg.get("timeframe", "4h")

    loader = MarketDataLoader(symbol=symbol, timeframe=timeframe, limit=1000) # Limit 可能在加载时不需要了
    loader.data_path = data_file # 动态设置数据文件路径
    df_full = loader.get_ohlcv()

    if df_full is None or len(df_full) < 200: # 需要足够数据进行指标计算和回测
        print(f"[Backtest] 失败：数据加载失败或数据不足 (需要 > 200, 实际: {len(df_full) if df_full is not None else 0})")
        return

    # state = MarketStateDetector() # SignalGenerator 内部会创建
    signal_generator = SignalGenerator(config) # 传入配置
    # AI 模型训练 (如果需要预训练)
    # print("Initial AI model training (if applicable)...")
    # predictor = signal_generator.predictor # 获取内部的 predictor
    # train_df = df_full.iloc[:int(len(df_full) * 0.8)] # 示例：用前 80% 数据训练
    # predictor.train_rolling(train_df) # 训练模型

    executor = TradeExecutor(config, simulate=True, df=df_full) # 传入完整数据用于滑点计算
    risk = RiskManager(config) # 使用配置初始化风控
    notifier = Notifier(config, enabled=False) # 传入配置，回测时禁用

    # --- 回测循环 ---
    logs = []
    initial_balance = config.get("risk", {}).get("initial_balance", 10000.0)
    risk.set_balance(initial_balance) # 设置初始资金
    print(f"[Backtest] Initial Balance: {initial_balance:.2f}")

    # 设定回测起点，确保有足够数据计算指标
    start_index = 100 # 例如，从第 100 根 K 线开始，确保前面有数据计算指标

    for i in range(start_index, len(df_full)):
        # 准备当前 K 线之前的数据窗口
        window = df_full.iloc[:i+1].copy() # 包含当前 K 线
        # 模拟器需要整个历史数据来算滑点，但信号生成器和风控只需要窗口数据
        executor.update_data(window) # 更新 executor 的数据用于滑点

        current_price = window['close'].iloc[-1]
        current_timestamp = window['timestamp'].iloc[-1]

        # 1. 生成信号
        signal = signal_generator.generate(window) # 传入窗口数据

        # 2. 处理现有持仓和潜在退出 (根据 SL/TP)
        #    这部分逻辑需要实现：检查当前价格是否触发了持仓的 SL 或 TP
        current_holdings = executor.get_holdings()
        # if current_holdings > 0:
        #     avg_entry = executor.get_average_entry_price()
        #     # 获取持仓时的止损止盈价 (需要存储)
        #     stored_sl, stored_tp = get_stored_sl_tp_for_position() # 需要实现
        #     if current_price <= stored_sl:
        #         print(f"[Backtest] STOP LOSS triggered at {current_price}")
        #         # 创建卖出订单以平仓
        #         exit_order = {... 'action': 'sell', 'amount': current_holdings ...}
        #         result = executor.execute(exit_order)
        #         # 更新余额，记录日志...
        #         continue # 处理完退出后跳过本轮入场信号
        #     elif current_price >= stored_tp:
        #         print(f"[Backtest] TAKE PROFIT triggered at {current_price}")
        #         # 创建卖出订单以平仓
        #         exit_order = {... 'action': 'sell', 'amount': current_holdings ...}
        #         result = executor.execute(exit_order)
        #         # 更新余额，记录日志...
        #         continue # 处理完退出后跳过本轮入场信号

        # 3. 处理入场信号
        if signal:
            action = signal["action"]
            confidence = signal["confidence"] # 可以用于过滤低置信度信号
            structure = signal["structure"]

            # 根据信号决定操作
            if action == "buy" and current_holdings == 0: # 如果没有持仓才考虑买入
                # 计算 ATR, SL/TP
                atr = risk.calculate_atr(window)
                stop_loss_price, take_profit_price = risk.calculate_sl_tp_prices(current_price, atr, action)

                if stop_loss_price is not None:
                    # 计算仓位大小
                    order_size = risk.calculate_position_size(current_price, stop_loss_price, symbol)

                    if order_size > 0:
                         # 验证交易是否允许
                        if risk.validate_trade(order_size, current_price):
                            # 创建订单字典
                            order = {
                                "symbol": symbol,
                                "action": action,
                                "amount": order_size, # 使用计算出的数量
                                "price": current_price, # 信号价格
                                "timestamp": current_timestamp,
                                "structure": structure,
                                "confidence": confidence,
                                # "stop_loss": stop_loss_price, # 可以传递给 executor 或另外存储
                                # "take_profit": take_profit_price
                            }

                            # 执行订单
                            result = executor.execute(order)

                            if result:
                                logs.append(result)
                                # 买入时不更新余额，卖出时根据 PnL 更新
                                # 可以在这里存储该笔持仓的 SL/TP 价格
                                # store_sl_tp_for_position(stop_loss_price, take_profit_price)
                                print(f"[Backtest] {i}: BUY executed. Size: {order_size:.6f}")
                        else:
                            print(f"[Backtest] {i}: Trade validation failed (Risk).")
                    else:
                         print(f"[Backtest] {i}: Calculated order size is zero.")
                else:
                     print(f"[Backtest] {i}: Could not calculate Stop Loss.")

            elif action == "sell" and current_holdings > 0: # 如果有持仓才考虑卖出 (平仓信号)
                 # 如果策略生成明确的平仓信号 (不仅仅是反向信号)
                 # 创建卖出订单以平掉所有仓位
                 exit_order = {
                      "symbol": symbol,
                      "action": "sell",
                      "amount": current_holdings, # 卖出全部持有
                      "price": current_price,
                      "timestamp": current_timestamp,
                      "structure": "exit_signal", # 标记为退出信号
                      "confidence": confidence
                 }
                 result = executor.execute(exit_order)
                 if result and result.get("pnl") is not None:
                      logs.append(result)
                      risk.update_balance(result["pnl"]) # 用 PnL 更新余额
                      print(f"[Backtest] {i}: SELL executed (Exit Signal). PnL: {result['pnl']:.2f}, New Balance: {risk.current_balance:.2f}")

            # elif action == "sell" and current_holdings == 0:
            #     # 处理做空信号 (如果策略支持)
            #     pass

        # 检查是否需要暂停交易 (每次迭代后检查)
        if not risk.validate_trade(0,0): # 传入虚拟值触发检查
             print(f"[Backtest] Trading paused due to max drawdown at index {i}. Stopping backtest.")
             break

        # AI 模型滚动训练 (示例)
        # update_interval = 7 * 6 # 假设每 7 天 (4h * 6 = 1 天) 更新一次
        # if i > start_index and i % update_interval == 0:
        #     print(f"Updating model at index {i}...")
        #     predictor.train_rolling(window) # 用当前窗口数据训练

    # --- 回测结束 ---
    final_balance = risk.current_balance
    total_pnl = final_balance - initial_balance
    pnl_pct = (total_pnl / initial_balance) * 100 if initial_balance else 0

    print("[Backtest] ✅ Finished.")
    if logs:
        df_logs = pd.DataFrame(logs)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        df_logs.to_csv(log_path, index=False)
        print(f"[Backtest] Results saved to {log_path}")
        print(f"[Backtest] Initial Balance: {initial_balance:.2f}")
        print(f"[Backtest] Final Balance:   {final_balance:.2f}")
        print(f"[Backtest] Total PnL:       {total_pnl:.2f} ({pnl_pct:.2f}%)")
        # 可以调用 PerformanceReport 进行更详细分析
        # from analysis.performance_report import PerformanceReport
        # reporter = PerformanceReport(log_path)
        # reporter.run_report(initial_balance) # 可能需要传入初始资金来计算回报率等
    else:
        print("[Backtest] ❗ No trades executed.")
        print(f"[Backtest] Final Balance: {final_balance:.2f} (No change)")

if __name__ == "__main__":
    config = load_config() # 加载配置
    # 示例：运行单个文件回测
    data_file = "core/data/historical/BTCUSDT_4h_new.csv" # 或者您的分割文件之一
    log_path = "logs/trade_log_backtest.csv"
    run_backtest(data_file, log_path, config)

    # # 示例：运行分割文件回测 (如果需要)
    # data_files = [
    #     "core/data/historical/BTCUSDT_4h_split_part_1.csv",
    #     "core/data/historical/BTCUSDT_4h_split_part_2.csv",
    #     "core/data/historical/BTCUSDT_4h_split_part_3.csv"
    # ]
    # for i, data_file in enumerate(data_files, 1):
    #     log_path = f"logs/trade_log_part_{i}.csv"
    #     print(f"\n=== Running backtest for part {i} ===")
    #     run_backtest(data_file, log_path, config)