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
