# run_live.py
import pandas as pd
import time
import traceback
from core.data_loader import MarketDataLoader
# from core.market_state import MarketStateDetector # 信号生成器内部会用
from core.signal_generator import SignalGenerator
from core.executor import TradeExecutor
from core.risk_manager import RiskManager
from core.notifier import Notifier
from core.config_loader import load_config # 引入配置加载
import ccxt # 引入 ccxt 用于获取实时数据

def fetch_live_data(exchange, symbol, timeframe, limit):
    """获取最新的K线数据"""
    try:
        # 获取最新的 'limit' 根K线
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not ohlcv:
            print("[Live] WARN: Fetched empty OHLCV data.")
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        # 检查最后一根K线是否完成 (根据时间戳判断) - 可选但推荐
        # last_candle_start_time = df['timestamp'].iloc[-1]
        # candle_duration = pd.Timedelta(exchange.timeframes[timeframe])
        # current_time_utc = pd.Timestamp.utcnow()
        # if current_time_utc < last_candle_start_time + candle_duration:
        #     print(f"[Live] INFO: Last candle ({last_candle_start_time}) might be incomplete. Using data up to the second to last candle.")
        #     return df.iloc[:-1] # 移除最后一根未完成的K线
        return df
    except ccxt.NetworkError as e:
        print(f"[Live] NetworkError fetching data: {e}")
    except ccxt.ExchangeError as e:
        print(f"[Live] ExchangeError fetching data: {e}")
    except Exception as e:
        print(f"[Live] Unexpected error fetching data: {e}")
    return None


def run_live():
    print("[Live] 🚀 Starting live trading...")
    config = load_config() # 加载配置

    # --- 初始化组件 ---
    trading_cfg = config.get("trading", {})
    symbol = trading_cfg.get("symbol", "BTC/USDT")
    timeframe = trading_cfg.get("timeframe", "4h")
    # 实时交易需要的数据量通常不需要很大，够计算指标就行
    data_limit_for_signal = 200 # 例如需要最近200根K线来计算指标

    # 初始化 ccxt 交易所
    binance_cfg = config.get("binance", {})
    exchange = ccxt.binance({
         'apiKey': binance_cfg.get("api_key"),
         'secret': binance_cfg.get("api_secret"),
         'enableRateLimit': True, # 启用内置的速率限制处理
         'options': {'defaultType': 'spot'} # 或 'future'/'margin'
    })
    try:
         exchange.load_markets()
         print("[Live] Successfully connected to Binance.")
    except Exception as e:
         print(f"[Live] FATAL: Failed to connect to Binance: {e}. Exiting.")
         return


    # loader = MarketDataLoader(...) # MarketDataLoader 主要用于加载历史数据，实时交易直接用 ccxt
    signal_generator = SignalGenerator(config)
    executor = TradeExecutor(config, simulate=False) # 使用真实交易模式
    risk = RiskManager(config)
    notifier = Notifier(config, enabled=config.get("telegram", {}).get("enabled", False))

    # 尝试从交易所获取当前余额和持仓来初始化 RiskManager 和 Executor
    try:
         balance = exchange.fetch_balance()
         quote_currency = symbol.split('/')[1]
         base_currency = symbol.split('/')[0]
         initial_balance_live = balance['total'][quote_currency] # 获取总余额 (包括冻结的)
         initial_holdings_live = balance['total'][base_currency] # 获取总持仓

         risk.set_balance(initial_balance_live)
         # executor.holdings_base_currency = initial_holdings_live # TODO: 需要更精细地处理 Executor 的持仓状态，特别是均价，最好从交易历史恢复或数据库加载
         print(f"[Live] Initial Balance from Binance: {initial_balance_live:.2f} {quote_currency}")
         # print(f"[Live] Initial Holdings from Binance: {initial_holdings_live:.6f} {base_currency}")

    except Exception as e:
         print(f"[Live] WARN: Could not fetch initial balance/holdings from Binance: {e}. Using default balance.")
         notifier.notify(f"⚠️ Warning: Could not fetch initial balance/holdings from Binance: {e}")
         # 使用配置中的默认初始值
         risk.set_balance(config.get("risk", {}).get("initial_balance", 10000.0))


    # --- 主循环 ---
    # 计算K线周期对应的秒数
    try:
        timeframe_duration_str = exchange.timeframes[timeframe]
        # 解析 '1m', '5m', '1h', '4h', '1d' 等
        if 'm' in timeframe_duration_str:
             sleep_seconds = int(timeframe_duration_str.replace('m', '')) * 60
        elif 'h' in timeframe_duration_str:
             sleep_seconds = int(timeframe_duration_str.replace('h', '')) * 60 * 60
        elif 'd' in timeframe_duration_str:
             sleep_seconds = int(timeframe_duration_str.replace('d', '')) * 60 * 60 * 24
        else:
             print(f"[Live] WARN: Cannot determine sleep duration for timeframe '{timeframe}'. Defaulting to 1 hour.")
             sleep_seconds = 3600
    except Exception as e:
        print(f"[Live] WARN: Error determining sleep duration: {e}. Defaulting to 1 hour.")
        sleep_seconds = 3600

    print(f"[Live] Main loop started. Symbol: {symbol}, Timeframe: {timeframe}. Checking every {sleep_seconds} seconds.")

    while True:
        loop_start_time = time.time()
        try:
            # 0. 检查风控是否暂停交易
            if not risk.validate_trade(0, 0):
                 print(f"[Live] Trading is paused due to max drawdown. Checking again in {sleep_seconds}s.")
                 time.sleep(sleep_seconds)
                 continue # 跳过本轮循环

            # 1. 获取最新数据
            print(f"[{pd.Timestamp.now()}] Fetching latest data for {symbol}...")
            df = fetch_live_data(exchange, symbol, timeframe, data_limit_for_signal)

            if df is None or len(df) < 100: # 确保有足够数据计算指标
                print(f"[Live] ⚠️ Data insufficient (need > 100, got: {len(df) if df is not None else 0}), skipping this cycle.")
                time.sleep(max(10, sleep_seconds // 4)) # 数据不足时稍等片刻再试
                continue

            executor.update_data(df) # 更新 executor 的数据用于滑点计算
            current_price = df['close'].iloc[-1]
            current_timestamp = df['timestamp'].iloc[-1]
            print(f"[Live] Latest data fetched. Current Price: {current_price:.2f}, Timestamp: {current_timestamp}")

            # 2. TODO: 检查当前持仓和 SL/TP 状态 (需要实现真实订单跟踪逻辑)
            #    - 查询交易所的未结订单 (止损/止盈单)
            #    - 查询当前实际持仓
            #    - 如果有活动的 SL/TP 订单被触发，处理相应逻辑，并可能跳过后续信号生成

            # 3. 生成交易信号
            print("[Live] Generating signal...")
            signal = signal_generator.generate(df) # 使用获取的最新数据生成信号

            if not signal:
                print("[Live] No signal generated.")
            else:
                print(f"[Live] Signal generated: {signal}")
                action = signal["action"]
                confidence = signal["confidence"]
                structure = signal["structure"]

                # TODO: 获取真实的当前持仓量
                current_holdings_real = 0.0 # Placeholder -需要从交易所或状态管理器获取
                # current_holdings_real = executor.get_holdings_from_exchange() # 假设有这个方法

                # 4. 根据信号和持仓执行操作
                if action == "buy" and current_holdings_real == 0: # 简单示例：只在无持仓时买入
                    # 计算 ATR, SL/TP
                    atr = risk.calculate_atr(df)
                    stop_loss_price, take_profit_price = risk.calculate_sl_tp_prices(current_price, atr, action)

                    if stop_loss_price is not None:
                        # 计算仓位大小
                        order_size = risk.calculate_position_size(current_price, stop_loss_price, symbol)

                        if order_size > 0:
                             # 验证交易
                            if risk.validate_trade(order_size, current_price):
                                # 创建订单
                                order = {
                                    "symbol": symbol, "action": action, "amount": order_size,
                                    "price": current_price, "timestamp": current_timestamp,
                                    "structure": structure, "confidence": confidence,
                                    # "stop_loss": stop_loss_price, # 可以传递给执行器
                                    # "take_profit": take_profit_price
                                }
                                print(f"[Live] Attempting to execute BUY order: {order}")
                                result = executor.execute(order) # 调用真实执行逻辑
                                if result and result.get("status") == "submitted": # 假设成功提交
                                     msg = f"✅ Live BUY Order Submitted: {order_size:.6f} {symbol}. Order ID: {result.get('order_id')}"
                                     print(msg)
                                     notifier.notify(msg)
                                     # TODO: 提交订单后，需要后续跟踪订单状态，并可能需要下止损止盈单
                                     # place_stop_loss_order(symbol, stop_loss_price, order_size)
                                     # place_take_profit_order(symbol, take_profit_price, order_size)
                                else:
                                     msg = f"⚠️ Live BUY Order Execution Failed/Not Implemented. Result: {result}"
                                     print(msg)
                                     notifier.notify(msg)
                            else:
                                 print(f"[Live] Trade validation failed (Risk).")
                        else:
                             print(f"[Live] Calculated order size is zero.")
                    else:
                         print(f"[Live] Could not calculate Stop Loss.")

                elif action == "sell" and current_holdings_real > 0: # 简单示例：只在有持仓时卖出 (平仓)
                     # 创建平仓订单
                     exit_order = {
                          "symbol": symbol, "action": "sell", "amount": current_holdings_real, # 卖出全部
                          "price": current_price, "timestamp": current_timestamp,
                          "structure": "exit_signal", "confidence": confidence
                     }
                     print(f"[Live] Attempting to execute SELL order (Exit): {exit_order}")
                     result = executor.execute(exit_order) # 调用真实执行逻辑
                     if result and result.get("status") == "submitted":
                          msg = f"✅ Live SELL Order Submitted (Exit): {current_holdings_real:.6f} {symbol}. Order ID: {result.get('order_id')}"
                          print(msg)
                          notifier.notify(msg)
                          # TODO: 如果之前有活动的 SL/TP 订单，需要取消它们
                          # cancel_active_sl_tp_orders(symbol)
                     else:
                          msg = f"⚠️ Live SELL Order Execution Failed/Not Implemented. Result: {result}"
                          print(msg)
                          notifier.notify(msg)

                # else: # 处理其他情况，如做空或无操作
                #     print("[Live] Signal action not applicable to current holdings state.")


        except Exception as e:
            err_msg = f"[Live] ❌ An error occurred in the main loop: {e}"
            print(err_msg)
            traceback.print_exc() # 打印详细错误堆栈
            try:
                notifier.notify(f"{err_msg}\n{traceback.format_exc()}") # 发送错误通知
            except Exception as notify_e:
                print(f"[Live] FATAL: Failed to send error notification: {notify_e}")

        # --- 循环结束，等待下一个周期 ---
        loop_end_time = time.time()
        elapsed = loop_end_time - loop_start_time
        wait_time = max(10, sleep_seconds - elapsed) # 至少等待10秒
        print(f"[Live] Cycle finished in {elapsed:.2f}s. Waiting for {wait_time:.2f}s until next check...")
        time.sleep(wait_time)


if __name__ == "__main__":
    run_live()