# strategies/trend_following.py

import pandas as pd
import numpy as np

class TrendFollowStrategy:
    def __init__(self, short_ma=10, long_ma=30, adx_period=14, adx_threshold=20):
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
        if len(df) < self.long_ma + self.adx_period + 2:
            return None

        df = df.copy()
        df['ma_short'] = df['close'].rolling(self.short_ma).mean()
        df['ma_long'] = df['close'].rolling(self.long_ma).mean()
        df['adx'] = self._calculate_adx(df)

        macd = df['macd'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        prev_macd = df['macd'].iloc[-2]
        prev_macd_signal = df['macd_signal'].iloc[-2]

        prev_short = df['ma_short'].iloc[-2]
        prev_long = df['ma_long'].iloc[-2]
        curr_short = df['ma_short'].iloc[-1]
        curr_long = df['ma_long'].iloc[-1]

        lookback = 10  # 缩短看回窗口
        prev_high = df['high'].iloc[-lookback:-1].max()
        prev_low = df['low'].iloc[-lookback:-1].min()
        current_price = df['close'].iloc[-1]

        if (prev_short < prev_long and curr_short > curr_long) or \
           (prev_macd < prev_macd_signal and macd > macd_signal) or \
           (current_price > prev_high):
            return {"action": "buy", "confidence": 0.5}
        elif (prev_short > prev_long and curr_short < curr_long) or \
             (prev_macd > prev_macd_signal and macd < macd_signal) or \
             (current_price < prev_low):
            return {"action": "sell", "confidence": 0.5}

        return None