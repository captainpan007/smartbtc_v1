# run_backtest.py
# (版本：整合了动态头寸规模和基础的 SL/TP 检查)

import pandas as pd
import time
import os
import traceback # 用于打印更详细的错误信息
from decimal import Decimal, ROUND_DOWN # 用于更精确的计算和截断


from core.data_loader import MarketDataLoader
from core.signal_generator import SignalGenerator
from core.executor import TradeExecutor
from core.risk_manager import RiskManager
from core.notifier import Notifier # 回测中通常禁用
from core.config_loader import load_config

from analysis.performance_report import PerformanceReport

def run_backtest(data_file, log_file_path, config):
    """
    运行回测的主要函数。

    Args:
        data_file (str): 回测使用的数据文件路径。
        log_file_path (str): 保存交易日志的文件路径。
        config (dict): 从 settings.yaml 加载的配置字典。
    """
    print(f"\n[Backtest] ⏳ Starting backtest for: {os.path.basename(data_file)}")
    print(f"[Backtest] Trade logs will be saved to: {log_file_path}")

    # --- 1. 初始化组件 ---
    trading_cfg = config.get("trading", {})
    symbol = trading_cfg.get("symbol", "BTC/USDT")
    timeframe = trading_cfg.get("timeframe", "4h")
    ai_cfg = config.get("ai_model", {})
    min_data_points_for_signal = ai_cfg.get("window_size", 180) + 20 # 需要足够数据计算指标+AI特征

    loader = MarketDataLoader(symbol=symbol, timeframe=timeframe)
    loader.data_path = data_file
    df_full = loader.get_ohlcv()

    if df_full is None or len(df_full) < min_data_points_for_signal:
        print(f"[Backtest] ❌ FAILED: Data loading error or insufficient data (Need > {min_data_points_for_signal}, Got: {len(df_full) if df_full is not None else 0})")
        return None # 返回 None 表示此部分回测失败

    print(f"[Backtest] Data loaded: {len(df_full)} rows, from {df_full['timestamp'].iloc[0]} to {df_full['timestamp'].iloc[-1]}")

    # 初始化信号生成器、执行器、风险管理器
    signal_generator = SignalGenerator(config)
    executor = TradeExecutor(config, simulate=True, df=df_full) # 模拟模式，传入数据用于滑点
    risk = RiskManager(config) # 使用配置初始化风控
    notifier = Notifier(config, enabled=False) # 回测时禁用通知

    # --- 2. 准备回测环境 ---
    logs = []
    initial_balance = risk.initial_balance # 从 RiskManager 获取初始资金
    risk.set_balance(initial_balance) # 确保设置当前余额
    print(f"[Backtest] Initial Balance: {initial_balance:.2f} USDT")

    # 回测起点，确保有足够数据计算指标和 AI 特征
    start_index = min_data_points_for_signal

    # 用于跟踪当前持仓状态和 SL/TP (非常重要！)
    active_trade = None # None 表示无持仓, 否则存储交易详情 e.g., {'entry_price': X, 'amount': Y, 'sl': Z, 'tp': W}

    # AI 模型初始训练 (如果需要) - 注意这里的训练数据范围
    train_size = int(len(df_full) * 0.8) # 或者使用固定的点数？
    train_df_initial = df_full.iloc[:start_index] # 使用回测开始前的数据进行初始训练更合理
    print(f"[Backtest] Performing initial AI model training using first {start_index} data points...")
    try:
         signal_generator.predictor.train(train_df_initial) # 假设 predictor 有 train 方法
    except Exception as e:
         print(f"[Backtest] WARNING: Initial AI training failed: {e}")

    # --- 3. 回测主循环 ---
    print(f"[Backtest] Starting main loop from index {start_index}...")
    for i in range(start_index, len(df_full)):
        # 准备当前 K 线及之前的数据窗口
        window_df = df_full.iloc[:i+1].copy() # 包含当前 K 线的数据窗口
        executor.update_data(window_df) # 更新 executor 的数据用于滑点计算

        current_price_high = window_df['high'].iloc[-1]
        current_price_low = window_df['low'].iloc[-1]
        current_price_close = window_df['close'].iloc[-1] # 通常用收盘价做决策，但 SL/TP 可能被 H/L 触发
        current_timestamp = window_df['timestamp'].iloc[-1]

        # 打印进度 (可选)
        if i % 100 == 0:
             print(f"[Backtest] Processing index {i}/{len(df_full)-1} | Time: {current_timestamp} | Balance: {risk.current_balance:.2f}")

        # --- 3a. 检查是否触发止损或止盈 (优先处理退出) ---
        exit_executed_this_step = False
        if active_trade:
            triggered_exit_price = None
            exit_reason = None

            # 检查止损 (假设做多，检查最低价是否低于止损价)
            if current_price_low <= active_trade['sl']:
                triggered_exit_price = active_trade['sl'] # 假设在止损价精确成交 (更保守)
                exit_reason = "Stop Loss"
            # 检查止盈 (假设做多，检查最高价是否高于止盈价)
            elif current_price_high >= active_trade['tp']:
                triggered_exit_price = active_trade['tp'] # 假设在止盈价精确成交 (更保守)
                exit_reason = "Take Profit"

            if triggered_exit_price is not None:
                exit_executed_this_step = True
                print(f"[Backtest] {i}: {exit_reason} triggered at price ~{triggered_exit_price:.2f}!")
                exit_order = {
                    "symbol": symbol,
                    "action": "sell",
                    "amount": active_trade['amount'], # 卖出持有的全部数量
                    "price": triggered_exit_price, # 使用触发价格作为信号价 (模拟时执行价会被滑点调整)
                    "timestamp": current_timestamp,
                    "structure": f"exit_{exit_reason.lower().replace(' ', '_')}",
                    "confidence": 1.0 # 强制退出
                }
                print(f"[Backtest] {i}: Attempting to execute {exit_reason} exit SELL order. Amount: {active_trade['amount']:.8f}")
                result = executor.execute(exit_order)
                if result and result.get("pnl") is not None:
                    logs.append(result)
                    pnl_from_trade = result["pnl"]
                    risk.update_balance(pnl_from_trade) # 更新余额
                    print(f"[Backtest] {i}: {exit_reason} SELL executed. PnL: {pnl_from_trade:.2f}, New Balance: {risk.current_balance:.2f}")
                    active_trade = None # 平仓后清除持仓状态
                else:
                    print(f"[Backtest] {i}: {exit_reason} SELL execution failed or no PnL returned. Critical error simulation might be needed.")
                    # 在真实交易中，如果退出失败是非常严重的问题
                    active_trade = None # 即使执行失败，也假设已尝试平仓，避免循环尝试

        # 如果本轮已执行退出，则跳过后续的入场信号检查
        if exit_executed_this_step:
            continue

        # --- 3b. 检查风控是否暂停交易 ---
        # (将检查放在这里，避免在触发SL/TP退出后还阻止退出)
        if not risk.validate_trade(0, 0): # 传入虚拟值触发检查 trading_paused
            if active_trade: # 如果有持仓，即使暂停也要允许因信号平仓
                 print(f"[Backtest] {i}: Trading paused (Max Drawdown), but holding position. Checking for SELL signal...")
            else:
                 # print(f"[Backtest] {i}: Trading paused (Max Drawdown). Skipping signal generation.")
                 continue # 如果无持仓且暂停，则跳过

        # --- 3c. 生成交易信号 ---
        signal = None
        try:
             # print(f"[Backtest] {i}: Generating signal...") # 减少日志噪音
             signal = signal_generator.generate(window_df)
        except Exception as e:
             print(f"[Backtest] {i}: ERROR during signal generation: {e}")
             # traceback.print_exc() # 取消注释以查看详细错误

        # --- 3d. 处理入场和信号平仓 ---
        if signal:
            action = signal["action"]
            confidence = signal.get("confidence", 0.0) # 确保 confidence 存在
            structure = signal.get("structure", "unknown")

            # --- 处理买入信号 (仅当无持仓时) ---
            if action == "buy" and active_trade is None:
                if risk.trading_paused: # 再次检查，如果刚才是因为持仓而没跳过
                    print(f"[Backtest] {i}: Trading paused (Max Drawdown). Skipping BUY signal.")
                    continue

                print(f"[Backtest] {i}: BUY signal received. Confidence: {confidence:.2f}. Current Price: {current_price_close:.2f}")

                # a. 计算 ATR
                atr = risk.calculate_atr(window_df)
                if atr <= 0:
                    print(f"[Backtest] {i}: ATR calculation failed or returned zero. Skipping BUY.")
                    continue

                # b. 计算止损价
                stop_loss_price, take_profit_price = risk.calculate_sl_tp_prices(current_price_close, atr, action)
                if stop_loss_price is None or stop_loss_price <= 0 or take_profit_price is None or take_profit_price <= stop_loss_price:
                    print(f"[Backtest] {i}: Failed to calculate valid SL/TP prices (SL: {stop_loss_price}, TP: {take_profit_price}). Skipping BUY.")
                    continue
                print(f"[Backtest] {i}: Calculated SL: {stop_loss_price:.2f}, TP: {take_profit_price:.2f} (ATR: {atr:.4f})")

                # c. 计算基于风险的头寸规模 (单位: BTC)
                order_size_btc = risk.calculate_position_size(
                    entry_price=current_price_close,
                    stop_loss_price=stop_loss_price,
                    symbol=symbol
                )
                if order_size_btc <= 0:
                    print(f"[Backtest] {i}: Calculated position size is zero or negative ({order_size_btc:.8f}). Check risk settings or balance. Skipping BUY.")
                    continue
                print(f"[Backtest] {i}: Calculated dynamic position size: {order_size_btc:.8f} BTC")

                # d. 验证交易 (风控暂停和资金)
                if not risk.validate_trade(order_size_btc, current_price_close):
                    required_quote_approx = order_size_btc * current_price_close
                    print(f"[Backtest] {i}: Trade validation failed (Risk paused or insufficient funds). Required USDT: ~{required_quote_approx:.2f}, Balance: {risk.current_balance:.2f}. Skipping BUY.")
                    continue

                # e. 创建订单字典
                order = {
                    "symbol": symbol,
                    "action": action,
                    "amount": order_size_btc,  # 使用动态计算的 BTC 数量
                    "price": current_price_close, # 信号价格
                    "timestamp": current_timestamp,
                    "structure": structure,
                    "confidence": confidence,
                }

                # f. 执行订单
                print(f"[Backtest] {i}: Attempting to execute BUY order...")
                result = executor.execute(order)

                if result and result.get('amount') > 0: # 确保成功执行且数量大于0
                    logs.append(result)
                    # 记录活动交易的状态
                    active_trade = {
                        'entry_price': result['price'], # 记录实际执行价格
                        'amount': result['amount'],     # 记录实际执行数量
                        'sl': stop_loss_price,          # 记录止损价
                        'tp': take_profit_price,          # 记录止盈价
                        'entry_time': current_timestamp
                    }
                    print(f"[Backtest] {i}: BUY executed successfully. Amount: {result['amount']:.8f}, Exec Price: {result['price']:.2f}. Active Trade: {active_trade}")
                else:
                    print(f"[Backtest] {i}: BUY execution failed or resulted in zero amount.")

            # --- 处理卖出信号 (仅当有持仓时，作为平仓信号) ---
            elif action == "sell" and active_trade is not None:
                print(f"[Backtest] {i}: SELL signal received (Exit Signal). Confidence: {confidence:.2f}. Exiting current position.")
                # 创建卖出订单以平掉所有仓位
                exit_order = {
                    "symbol": symbol,
                    "action": "sell",
                    "amount": active_trade['amount'], # 卖出持有的全部数量
                    "price": current_price_close,    # 使用当前收盘价作为信号价
                    "timestamp": current_timestamp,
                    "structure": f"exit_signal_{structure}", # 标记为信号退出
                    "confidence": confidence
                }
                print(f"[Backtest] {i}: Attempting to execute SELL order (Signal Exit). Amount: {active_trade['amount']:.8f}")
                result = executor.execute(exit_order)
                if result and result.get("pnl") is not None:
                    logs.append(result)
                    pnl_from_trade = result["pnl"]
                    risk.update_balance(pnl_from_trade) # 更新余额
                    print(f"[Backtest] {i}: SELL executed (Signal Exit). PnL: {pnl_from_trade:.2f}, New Balance: {risk.current_balance:.2f}")
                    active_trade = None # 平仓后清除持仓状态
                else:
                    print(f"[Backtest] {i}: SELL execution (Signal Exit) failed or no PnL returned.")
                    active_trade = None # 即使失败也假设尝试退出

        # --- 3e. AI 模型滚动训练 (如果启用) ---
        update_interval = 7 * 6 # 假设每 7 天 (4h * 6 = 1 天) 更新一次
        if i > start_index and i % update_interval == 0:
            print(f"[Backtest] {i}: Updating AI model...")
            try:
                 # 使用到当前行为止的数据进行训练 (可能需要调整 predictor 的方法)
                 signal_generator.predictor.train_rolling(window_df)
            except Exception as e:
                 print(f"[Backtest] WARNING: AI model rolling update failed at index {i}: {e}")

    # --- 4. 回测结束与报告 ---
    final_balance = risk.current_balance
    total_pnl = final_balance - initial_balance
    pnl_pct = (total_pnl / initial_balance) * 100 if initial_balance else 0

    print(f"\n[Backtest] ✅ Finished backtesting for: {os.path.basename(data_file)}")
    print(f"[Backtest] Initial Balance: {initial_balance:.2f} USDT")
    print(f"[Backtest] Final Balance:   {final_balance:.2f} USDT")
    print(f"[Backtest] Total PnL:       {total_pnl:.2f} USDT ({pnl_pct:.2f}%)")
    print(f"[Backtest] Peak Balance:    {risk.peak_balance:.2f} USDT") # 显示峰值资金
    drawdown = (1 - final_balance / risk.peak_balance) * 100 if risk.peak_balance > 0 else 0
    print(f"[Backtest] Final Drawdown:  {drawdown:.2f}% from peak") # 显示最终的回撤

    if logs:
        df_logs = pd.DataFrame(logs)
        try:
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            df_logs.to_csv(log_file_path, index=False)
            print(f"[Backtest] Trade logs saved to: {log_file_path}")

            # 可以调用 PerformanceReport 进行更详细分析
            print("[Backtest] Generating performance report...")
            try:
                reporter = PerformanceReport(log_file_path) # 假设类已定义
                report_summary = reporter.run_report(initial_balance)
                print(report_summary) # 打印报告摘要
            except Exception as report_e:
                print(f"[Backtest] WARNING: Failed to generate performance report: {report_e}")

        except Exception as e:
            print(f"[Backtest] ERROR: Failed to save trade logs to {log_file_path}: {e}")

        # 返回一些关键指标供聚合分析
        results_summary = {
            "data_file": os.path.basename(data_file),
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "total_pnl": total_pnl,
            "pnl_pct": pnl_pct,
            "peak_balance": risk.peak_balance,
            "final_drawdown_pct": drawdown,
            "num_trades": len(df_logs[df_logs['action'] == 'sell']) # 统计卖出次数作为交易次数
        }
        return results_summary

    else:
        print("[Backtest] ❗ No trades were executed in this period.")
        return { # 即使没有交易也返回摘要
            "data_file": os.path.basename(data_file),
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "total_pnl": 0.0,
            "pnl_pct": 0.0,
            "peak_balance": initial_balance,
            "final_drawdown_pct": 0.0,
            "num_trades": 0
        }


if __name__ == "__main__":
    config = load_config("config/settings.yaml") # 明确指定配置文件路径

    # 定义数据文件列表 (从您的 GitHub 结构推断)
    data_dir = "core/data/historical"
    data_files = [
        os.path.join(data_dir, "BTCUSDT_4h_split_part_1.csv"),
        os.path.join(data_dir, "BTCUSDT_4h_split_part_2.csv"),
        os.path.join(data_dir, "BTCUSDT_4h_split_part_3.csv"),
        os.path.join(data_dir, "BTCUSDT_4h_split_part_4.csv"),
        os.path.join(data_dir, "BTCUSDT_4h_split_part_5.csv"),
    ]

    # 检查文件是否存在
    valid_data_files = [f for f in data_files if os.path.exists(f)]
    if not valid_data_files:
        print("❌ ERROR: No valid data files found in the specified paths. Please check the paths in run_backtest.py.")
    else:
        print(f"Found {len(valid_data_files)} data files to process.")

        all_results = []
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True) # 确保日志目录存在

        # --- 运行回测 ---
        for i, data_file in enumerate(valid_data_files, 1):
            log_path = os.path.join(log_dir, f"trade_log_part_{i}.csv")
            part_results = run_backtest(data_file, log_path, config)
            if part_results:
                all_results.append(part_results)

        # --- 聚合结果 (示例) ---
        if all_results:
            print("\n\n====== Overall Backtest Summary ======")
            df_results = pd.DataFrame(all_results)
            print(df_results.to_string(index=False))

            total_trades = df_results['num_trades'].sum()
            # 注意：这里的总体 PnL 和回报率计算可能需要更复杂的方法
            # 例如，不能简单地将各部分的 PnL 相加，因为资金基数变了
            # 需要模拟连续的资金曲线或使用更高级的组合分析
            print(f"\nTotal Trades Executed (Sell count): {total_trades}")
            # 简单计算总 PnL 供参考，但不完全准确
            total_pnl_sum = df_results['total_pnl'].sum()
            print(f"Sum of PnL across all parts: {total_pnl_sum:.2f} USDT (Note: Not a perfect portfolio simulation)")
        else:
            print("\nNo results generated from backtests.")