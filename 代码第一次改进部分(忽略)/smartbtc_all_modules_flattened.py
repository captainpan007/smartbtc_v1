# === 项目目录结构 ===
# -------------------
# smartbtc_v1/
#   ├── __init__.py
#   ├── backtester.py
#   ├── performance_report.py
#   ├── config_loader.py
#   ├── __init__.py
#   ├── config_loader.py
#   ├── data_loader.py
#   ├── executor.py
#   ├── market_state.py
#   ├── notifier.py
#   ├── risk_manager.py
#   ├── signal_generator.py
#   ├── strategy_switcher.py
# ├── fetch_binance_data.py
# ├── run_backtest.py
# ├── run_live.py
#   ├── __init__.py
#   ├── market_regime.py
#   ├── mean_reversion.py
#   ├── trend_following.py
#   ├── __init__.py
#   ├── indicators.py
# 

# === 所有模块代码汇总（含注释） ===


# ============================================================
# 模块: fetch_binance_data.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
import ccxt
import pandas as pd

# 初始化 Binance
exchange = ccxt.binance()

# 参数设置
symbol = "BTC/USDT"
timeframe = "4h"
limit = 1000  # 可修改为更大，如1500

# 获取数据
ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

# 转换为 DataFrame
df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

# 保存路径（你的项目中指定位置）
save_path = r"F:\量化交易算法\smartbtc_v1\core\data\historical\BTCUSDT_4h.csv"
df.to_csv(save_path, index=False)

print(f"✅ 数据已保存到：{save_path}")


# ============================================================
# 模块: run_backtest.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
from core.data_loader import MarketDataLoader
from core.market_state import MarketStateDetector
from core.strategy_switcher import StrategySwitcher
from core.executor import TradeExecutor
from core.risk_manager import RiskManager
from core.notifier import Notifier
from core.signal_generator import SignalGenerator  # ✅ 加上这行

import pandas as pd
import time
import os

LOG_PATH = "logs/trade_log.csv"

def run_backtest():
    print("[Backtest] ⏳ Starting backtest...")

    loader = MarketDataLoader(symbol="BTC/USDT", timeframe="4h", limit=200)
    state = MarketStateDetector()
    signal_generator = SignalGenerator()
    executor = TradeExecutor(simulate=True)
    risk = RiskManager()
    notifier = Notifier(enabled=False)

    df = loader.get_ohlcv()
    logs = []

    for i in range(100, len(df)):
        window = df.iloc[:i].copy()
        current_price = window['close'].iloc[-1]

        signal = signal_generator.generate(window)
        if not signal:
            continue


        order = {
            "symbol": "BTC/USDT",
            "action": signal["action"],
            "amount": 100,
            "timestamp": window['timestamp'].iloc[-1],
            "price": current_price,
            "structure": signal["structure"],
            "confidence": signal["confidence"]  # 可选加入，辅助决策
            
        }

        if not risk.validate(order):
            continue

        result = executor.execute(order)
        if result:
            logs.append(result)
            notifier.notify(result)

    if logs:
        df_logs = pd.DataFrame(logs)
        os.makedirs("logs", exist_ok=True)
        df_logs.to_csv(LOG_PATH, index=False)
        print(f"[Backtest] ✅ Finished. Results saved to {LOG_PATH}")
    else:
        print("[Backtest] ❗ No trades executed.")

if __name__ == "__main__":
    run_backtest()


# ============================================================
# 模块: run_live.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
from core.data_loader import MarketDataLoader
from core.market_state import MarketStateDetector
from core.strategy_switcher import StrategySwitcher
from core.executor import TradeExecutor
from core.risk_manager import RiskManager
from core.notifier import Notifier
from core.signal_generator import SignalGenerator  # ✅ 加上这行
import time
import traceback

SYMBOL = "BTC/USDT"
INTERVAL = "4h"
SLEEP_SECONDS = 60 * 60 * 4

def run_live():
    print("[Live] 🚀 Starting live trading...")

    loader = MarketDataLoader(symbol=SYMBOL, timeframe=INTERVAL, limit=200)
    signal_generator = SignalGenerator()
    executor = TradeExecutor(simulate=False)
    risk = RiskManager()
    notifier = Notifier(enabled=True)

    while True:
        try:
            df = loader.get_ohlcv()
            if df is None or len(df) < 100:
                print("[Live] ⚠️ 数据不足，跳过本轮。")
                time.sleep(SLEEP_SECONDS)
                continue

            current_price = df['close'].iloc[-1]
            signal = signal_generator.generate(window)
            if not signal:
                continue


            order = {
                "symbol": "BTC/USDT",
                "action": signal["action"],
                "amount": 100,
                "timestamp": window['timestamp'].iloc[-1],
                "price": current_price,
                "structure": signal["structure"],
                "confidence": signal["confidence"]
}


            if risk.validate(order):
                result = executor.execute(order)
                notifier.notify(result)
            else:
                print("[Live] 🛑 风控不通过，信号忽略。")

        except Exception as e:
            print(f"[Live ❌ Error] {e}")
            traceback.print_exc()
            notifier.notify(f"❌ Live Trading Error: {str(e)}")

        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    run_live()


# ============================================================
# 模块: analysis/__init__.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================



# ============================================================
# 模块: analysis/backtester.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# analysis/backtester.py

import os
import pandas as pd
import matplotlib.pyplot as plt
from core.data_loader import load_historical_data
from core.signal_generator import SignalGenerator
from core.market_state import MarketStateIdentifier
from core.strategy_switcher import StrategySwitcher
from core.risk_manager import RiskManager
from core.execution.executor import BacktestExecutor
from utils.indicators import calculate_atr


class Backtester:
    def __init__(self, data_path, starting_balance=1000):
        self.data_path = data_path
        self.data = load_historical_data(data_path)
        self.balance = starting_balance
        self.market_state_identifier = MarketStateIdentifier()
        self.strategy_switcher = StrategySwitcher()
        self.signal_generator = SignalGenerator()
        self.risk_manager = RiskManager()
        self.executor = BacktestExecutor(starting_balance=starting_balance)
        self.logs = []

    def run(self):
        print("[Backtester] Running backtest...")

        for i in range(50, len(self.data)):
            window = self.data.iloc[:i].copy().reset_index(drop=True)
            current_price = window['close'].iloc[-1]

            # 1. 判断市场状态
            market_state = self.market_state_identifier.identify(window)
            strategy_name = self.strategy_switcher.select(market_state)

            # 2. 生成信号
            signal = self.signal_generator.generate(window, strategy_name)
            signal['strategy'] = strategy_name

            # 3. 动态止损计算（真实 ATR）
            atr = calculate_atr(window)
            stop_loss_distance = atr * 2
            signal['stop_loss'] = current_price - stop_loss_distance
            signal['take_profit'] = current_price + stop_loss_distance * 1.5

            # 4. 资金管理
            position_size = self.risk_manager.calculate_position_size(
                current_balance=self.executor.balance,
                stop_loss_distance=stop_loss_distance
            )
            signal['amount'] = position_size

            # 5. 执行交易
            execution_result = self.executor.execute(signal, current_price)
            if execution_result:
                self.logs.append(execution_result)

            # 6. 回撤控制
            if self.executor.max_drawdown_exceeded():
                print("[Backtester] ❌ Max drawdown exceeded. Stopping backtest.")
                break

        print("[Backtester] ✅ Completed.")
        self._visualize()

    def _visualize(self):
        balances = self.executor.get_balances()
        plt.figure(figsize=(10, 4))
        plt.plot(balances, label="Equity")
        plt.title("Backtest Equity Curve")
        plt.xlabel("Trade Index")
        plt.ylabel("Balance")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    backtester = Backtester(data_path="core/data/historical/BTCUSDT_4h.csv")
    backtester.run()


# ============================================================
# 模块: analysis/performance_report.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# analysis/performance_report.py

import pandas as pd
import matplotlib.pyplot as plt
import os

class PerformanceReport:
    def __init__(self, log_path="logs/trade_log.csv"):
        self.log_path = log_path
        self.df = None

    def load_data(self):
        if not os.path.exists(self.log_path):
            raise FileNotFoundError(f"[Error] Log file not found: {self.log_path}")
        self.df = pd.read_csv(self.log_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

    def compute_metrics(self):
        if self.df is None:
            self.load_data()

        trades = self.df[self.df['action'].isin(['buy', 'sell'])].copy()
        trades['pnl'] = trades['pnl'].fillna(0)

        win_trades = trades[trades['pnl'] > 0]
        loss_trades = trades[trades['pnl'] < 0]

        winrate = len(win_trades) / len(trades) * 100 if len(trades) > 0 else 0
        avg_win = win_trades['pnl'].mean() if not win_trades.empty else 0
        avg_loss = loss_trades['pnl'].mean() if not loss_trades.empty else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        net_profit = trades['pnl'].sum()

        return {
            "Total Trades": len(trades),
            "Win Rate": round(winrate, 2),
            "Avg Win": round(avg_win, 2),
            "Avg Loss": round(avg_loss, 2),
            "Profit Factor": round(profit_factor, 2),
            "Net Profit": round(net_profit, 2)
        }

    def plot_pnl_curve(self):
        if self.df is None:
            self.load_data()
        self.df['cumulative_pnl'] = self.df['pnl'].fillna(0).cumsum()

        plt.figure(figsize=(10, 5))
        plt.plot(self.df['timestamp'], self.df['cumulative_pnl'], label="Cumulative PnL")
        plt.title("Cumulative PnL Over Time")
        plt.xlabel("Time")
        plt.ylabel("PnL (USDT)")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def plot_win_loss_distribution(self):
        if self.df is None:
            self.load_data()

        pnl = self.df['pnl'].dropna()
        plt.figure(figsize=(8, 4))
        plt.hist(pnl, bins=30, color='steelblue', edgecolor='black')
        plt.title("PnL Distribution")
        plt.xlabel("Profit / Loss")
        plt.ylabel("Frequency")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def run_report(self):
        metrics = self.compute_metrics()
        print("\n📊 Performance Summary:")
        for k, v in metrics.items():
            print(f"{k}: {v}")
        self.plot_pnl_curve()
        self.plot_win_loss_distribution()


# ============================================================
# 模块: config/config_loader.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
import yaml
import os
def load_config(path="config/settings.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# 模块: core/__init__.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================



# ============================================================
# 模块: core/config_loader.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# core/config_loader.py

import yaml
import os

def load_config(path="config/settings.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# 模块: core/data_loader.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# core/data_loader.py

import requests

class MarketDataLoader:
    def __init__(self, symbol="BTC/USDT", timeframe="1h", limit=200):
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit

    def get_ohlcv(self):
        # 这里可换成从本地CSV或ccxt读取
        import pandas as pd
        return pd.read_csv("core/data/historical/BTCUSDT_4h.csv")

    def get_fear_greed(self):
        try:
            res = requests.get("https://api.alternative.me/fng/", timeout=5)
            return res.json()["data"][0]
        except Exception as e:
            print(f"FG Index Error: {e}")
            return {"value": 50}  # 默认中性

    def get_onchain_metrics(self):
        try:
            # 示例伪造指标
            return {"active_addresses": 1000000, "exchange_volume": 50000}
        except Exception as e:
            print(f"OnChain Error: {e}")
            return {}


# ============================================================
# 模块: core/executor.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# core/executor.py

from core.config_loader import load_config

class TradeExecutor:
    def __init__(self, simulate=False):
        self.simulate = simulate
        config = load_config()
        self.api_key = config["binance"]["api_key"]
        self.api_secret = config["binance"]["api_secret"]
        # 可扩展：初始化 Binance 客户端等

    def execute(self, order):
        if self.simulate:
            return self._simulate_order(order)
        else:
            return self._real_order(order)

    def _simulate_order(self, order):
        print(f"[Simulated] {order['action'].upper()} {order['amount']} {order['symbol']} @ {order['price']} 结构={order['structure']}")
        return {
            "symbol": order["symbol"],
            "action": order["action"],
            "price": order["price"],
            "amount": order["amount"],
            "timestamp": order["timestamp"],
            "structure": order["structure"],
            "regime": order.get("regime", "unknown")
        }

    def _real_order(self, order):
        # 💡 待实现真实下单逻辑
        print(f"[REAL] 下单模块尚未实现。订单信息如下：{order}")
        return {
            "symbol": order["symbol"],
            "action": order["action"],
            "price": order["price"],
            "amount": order["amount"],
            "timestamp": order["timestamp"],
            "structure": order["structure"],
            "regime": order.get("regime", "unknown")
        }


# ============================================================
# 模块: core/market_state.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# market/market_state_detector.py

# core/market_state.py

import pandas as pd
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange

class MarketStateDetector:
    def __init__(self, adx_threshold=25, atr_window=14):
        self.adx_threshold = adx_threshold
        self.atr_window = atr_window

    def detect_state(self, df: pd.DataFrame) -> str:
        """
        输入：包含 ['high', 'low', 'close'] 列的 DataFrame
        输出："trending" 或 "ranging"
        """

        if len(df) < self.atr_window + 10:
            return "unknown"  # 数据不足

        try:
            adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14).adx()
            atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=self.atr_window).average_true_range()
            latest_adx = adx.iloc[-1]
            latest_atr = atr.iloc[-1]
            close_price = df['close'].iloc[-1]
            atr_ratio = latest_atr / close_price  # 用于辅助判断波动率是否过低

            # 条件判断
            if latest_adx >= self.adx_threshold and atr_ratio > 0.01:
                return "trending"
            elif latest_adx < self.adx_threshold or atr_ratio < 0.008:
                return "ranging"
            else:
                return "neutral"
        except Exception as e:
            print(f"[MarketStateDetector] Error: {e}")
            return "unknown"


# ✅ 示例使用（调试用）
if __name__ == "__main__":
    import ccxt
    import datetime

    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv("BTC/USDT", timeframe="4h", limit=200)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    detector = MarketStateDetector()
    state = detector.detect_state(df)
    print(f"📊 市场状态：{state}")


# ============================================================
# 模块: core/notifier.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# ✅ 通知模块：core/notifier.py
# 功能：通过 Telegram Bot 向群组或个人发送交易信号或警报


# core/notifier.py

from core.config_loader import load_config
import requests

class Notifier:
    def __init__(self, enabled=True):
        self.enabled = enabled
        cfg = load_config().get("telegram", {})
        self.token = cfg.get("bot_token", "")
        self.chat_id = cfg.get("chat_id", "")

    def notify(self, message):
        if not self.enabled or not self.token or not self.chat_id:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}
        try:
            requests.post(url, data=payload, timeout=5)
        except Exception as e:
            print(f"[Notifier] ❌ Telegram Error: {e}")


# ============================================================
# 模块: core/risk_manager.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# core/risk_manager.py

import os
from core.config_loader import load_config

class RiskManager:
    def __init__(self, initial_balance=1000):
        config = load_config()
        risk_cfg = config.get("risk", {})

        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.current_balance = initial_balance
        self.atr_multiplier = risk_cfg.get("sl_multiplier", 2.0)
        self.max_drawdown = risk_cfg.get("max_drawdown_pct", 0.2)
        self.position_risk_pct = risk_cfg.get("max_position_pct", 0.02)
        self.trading_paused = False
        self.pause_log = "logs/drawdown_monitor.log"

        os.makedirs(os.path.dirname(self.pause_log), exist_ok=True)

    def update_balance(self, new_balance):
        self.current_balance = new_balance
        self.peak_balance = max(self.peak_balance, new_balance)

        drawdown = 1 - self.current_balance / self.peak_balance
        if drawdown > self.max_drawdown:
            self.trading_paused = True
            with open(self.pause_log, "a") as f:
                f.write(f"[ALERT] Max drawdown exceeded! Current: {drawdown:.2%}\n")

    def calculate_stop_loss(self, atr):
        return self.atr_multiplier * atr

    def calculate_position_size(self, symbol_price):
        risk_amount = self.current_balance * self.position_risk_pct
        return round(risk_amount / symbol_price, 6)

    def is_trading_allowed(self):
        return not self.trading_paused

    def validate(self, order):
        if not self.is_trading_allowed():
            print("[Risk] 🚫 交易暂停（达到最大回撤）")
            return False
        return True

    def reset(self):
        self.trading_paused = False
        self.peak_balance = self.current_balance
        with open(self.pause_log, "a") as f:
            f.write(f"[INFO] Trading resumed. Peak reset to {self.peak_balance:.2f}\n")


# ============================================================
# 模块: core/signal_generator.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# core/signal_generator.py

import pandas as pd
from strategies.mean_reversion import MeanReversionStrategy
from strategies.trend_following import TrendFollowStrategy
from utils.indicators import calculate_rsi, calculate_bollinger_bands, calculate_adx
from core.market_state import MarketStateDetector
from core.data_loader import MarketDataLoader


class SignalGenerator:
    def __init__(self):
        self.mean_reversion = MeanReversionStrategy()
        self.trend_following = TrendFollowStrategy()
        self.market_state = MarketStateDetector()
        self.loader = MarketDataLoader(symbol="BTC/USDT", timeframe="1h", limit=200)

    def generate(self, df: pd.DataFrame, symbol="BTC/USDT") -> dict:
        signals = []

        # ========== 1. 技术信号 ==========
        df = df.copy()
        df['rsi'] = calculate_rsi(df['close'], window=14)
        df = calculate_bollinger_bands(df, window=20)
        df['adx'] = calculate_adx(df)

        # ========== 2. 市场状态识别 ==========
        market_condition = self.market_state.detect_state(df)

        # ========== 3. 情绪指标 ==========
        fear_greed = self.loader.get_fear_greed()
        fg_level = fear_greed.get("value", 50)

        # ========== 4. 链上数据指标 ==========
        onchain = self.loader.get_onchain_metrics()
        active_addresses = onchain.get("active_addresses", 0)
        exchange_volume = onchain.get("exchange_volume", 0)

        # ========== 5. 策略信号融合 ==========
        strategy_type = "trend_following"
        signal_data = self.trend_following.check(df)

        if market_condition == "ranging":
            strategy_type = "mean_reversion"
            signal_data = self.mean_reversion.check(df)

        # ========== 6. 信号格式封装 ==========
        if signal_data and isinstance(signal_data, dict) and "action" in signal_data:
            signals.append({
                "symbol": symbol,
                "action": signal_data["action"],
                "confidence": signal_data.get("confidence", 0.5),
                "structure": strategy_type,
                "meta": {
                    "rsi": df["rsi"].iloc[-1],
                    "adx": df["adx"].iloc[-1],
                    "fg_index": fg_level,
                    "onchain_active": active_addresses,
                    "onchain_volume": exchange_volume
                }
            })

        return signals[0] if signals else None


# ============================================================
# 模块: core/strategy_switcher.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# ✅ 策略动态切换模块
# core/strategy_switcher.py

from core.market_state import MarketStateDetector
from strategies.mean_reversion import MeanReversionStrategy
from strategies.trend_following import TrendFollowStrategy

class StrategySwitcher:
    def __init__(self):
        self.market_state_detector = MarketStateDetector()
        self.mean_reversion = MeanReversionStrategy()
        self.trend_following = TrendFollowStrategy()

    def select(self, df):
        """
        根据市场状态选择对应策略实例
        """
        state = self.market_state_detector.detect_state(df)
        if state == "ranging":
            print("📉 市场震荡 → 启用均值回归策略")
            return self.mean_reversion
        elif state == "trending":
            print("📈 市场趋势 → 启用趋势跟踪策略")
            return self.trend_following
        else:
            print("⏸ 市场状态未知 → 不生成信号")
            return None


# ============================================================
# 模块: strategies/__init__.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================



# ============================================================
# 模块: strategies/market_regime.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# smartbtc_v1/strategies/market_regime.py

import pandas as pd
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange

class MarketRegimeDetector:
    def __init__(self, adx_period=14, adx_threshold=20, atr_window=14, volatility_threshold=0.015):
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.atr_window = atr_window
        self.volatility_threshold = volatility_threshold

    def detect_by_adx(self, df: pd.DataFrame) -> str:
        """通过 ADX 指标判断市场状态：趋势 或 震荡"""
        adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=self.adx_period).adx()
        if adx.iloc[-1] >= self.adx_threshold:
            return 'trend'
        else:
            return 'range'

    def detect_by_volatility(self, df: pd.DataFrame) -> str:
        """通过波动率判断市场状态"""
        df = df.copy()
        df['return'] = df['close'].pct_change()
        rolling_volatility = df['return'].rolling(window=self.atr_window).std()
        if rolling_volatility.iloc[-1] > self.volatility_threshold:
            return 'trend'
        else:
            return 'range'

    def detect(self, df: pd.DataFrame, method="adx") -> str:
        """
        综合判断方法：
        - method="adx": 使用 ADX 判断
        - method="volatility": 使用波动率判断
        """
        if method == "adx":
            return self.detect_by_adx(df)
        elif method == "volatility":
            return self.detect_by_volatility(df)
        else:
            raise ValueError(f"Unsupported detection method: {method}")


# ✅ 示例用法（建议写入 notebook 或回测逻辑中调用）
if __name__ == "__main__":
    import ccxt
    import pandas as pd
    from datetime import datetime

    exchange = ccxt.binance()
    bars = exchange.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=100)
    df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    detector = MarketRegimeDetector()
    result = detector.detect(df, method="adx")
    print(f"[Regime] 当前市场状态判断为：{result}")


# ============================================================
# 模块: strategies/mean_reversion.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# strategies/mean_reversion.py

import pandas as pd
import numpy as np

class MeanReversionStrategy:
    def __init__(self, rsi_period=14, rsi_low=30, rsi_high=70, bb_period=20, bb_std=2):
        self.rsi_period = rsi_period
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.bb_period = bb_period
        self.bb_std = bb_std

    def rsi(self, series):
        delta = series.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def bollinger_bands(self, series):
        ma = series.rolling(self.bb_period).mean()
        std = series.rolling(self.bb_period).std()
        upper = ma + self.bb_std * std
        lower = ma - self.bb_std * std
        return upper, lower

    def check(self, df):
        if len(df) < max(self.rsi_period, self.bb_period):
            return None

        df = df.copy()
        df['rsi'] = self.rsi(df['close'])
        df['bb_upper'], df['bb_lower'] = self.bollinger_bands(df['close'])

        last = df.iloc[-1]
        price = last['close']
        rsi_val = last['rsi']
        bb_upper = last['bb_upper']
        bb_lower = last['bb_lower']

        if np.isnan(rsi_val) or np.isnan(bb_upper) or np.isnan(bb_lower):
            return None

        # 超卖 + 跌破下轨 → 买入信号
        if rsi_val < self.rsi_low and price < bb_lower:
            confidence = min(1.0, (self.rsi_low - rsi_val) / 20 + 0.5)
            return {
                "action": "buy",
                "confidence": round(confidence, 2)
            }

        # 超买 + 突破上轨 → 卖出信号
        elif rsi_val > self.rsi_high and price > bb_upper:
            confidence = min(1.0, (rsi_val - self.rsi_high) / 20 + 0.5)
            return {
                "action": "sell",
                "confidence": round(confidence, 2)
            }

        return None


# ============================================================
# 模块: strategies/trend_following.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# strategies/trend_following.py

import pandas as pd
import numpy as np

class TrendFollowStrategy:
    def __init__(self, short_ma=20, long_ma=50, adx_period=14, adx_threshold=25):
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold

    def _calculate_adx(self, df):
        high = df['high']
        low = df['low']
        close = df['close']

        plus_dm = high.diff()
        minus_dm = low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0

        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(self.adx_period).mean()
        plus_di = 100 * (plus_dm.rolling(self.adx_period).mean() / atr)
        minus_di = 100 * (abs(minus_dm).rolling(self.adx_period).mean() / atr)

        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(self.adx_period).mean()

        return adx

    def check(self, df):
        if len(df) < self.long_ma + self.adx_period:
            return None

        df = df.copy()
        df['ma_short'] = df['close'].rolling(self.short_ma).mean()
        df['ma_long'] = df['close'].rolling(self.long_ma).mean()
        df['adx'] = self._calculate_adx(df)

        adx_val = df['adx'].iloc[-1]
        if adx_val is None or np.isnan(adx_val) or adx_val < self.adx_threshold:
            return None  # 趋势不强，不出信号

        # 判断交叉
        prev_short = df['ma_short'].iloc[-2]
        prev_long = df['ma_long'].iloc[-2]
        curr_short = df['ma_short'].iloc[-1]
        curr_long = df['ma_long'].iloc[-1]

        if prev_short < prev_long and curr_short > curr_long:
            return {
                "action": "buy",
                "confidence": min(1.0, adx_val / 50)  # 用 ADX 强度推断置信度
            }
        elif prev_short > prev_long and curr_short < curr_long:
            return {
                "action": "sell",
                "confidence": min(1.0, adx_val / 50)
            }

        return None


# ============================================================
# 模块: utils/__init__.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================



# ============================================================
# 模块: utils/indicators.py
# 功能说明: ⬇️ 请由你或审阅人补充功能描述
# ============================================================
# utils/indicators.py

import pandas as pd

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(df, window=20, num_std=2):
    df = df.copy()
    df["ma"] = df["close"].rolling(window).mean()
    df["std"] = df["close"].rolling(window).std()
    df["upper"] = df["ma"] + num_std * df["std"]
    df["lower"] = df["ma"] - num_std * df["std"]
    return df

def calculate_adx(df, period=14):
    df = df.copy()
    high = df["high"]
    low = df["low"]
    close = df["close"]

    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (abs(minus_dm).rolling(period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(period).mean()

    return adx
