# strategies/mean_reversion.py

import pandas as pd
import numpy as np

class MeanReversionStrategy:
    def __init__(self, rsi_period=14, rsi_low=40, rsi_high=60, ma_period=20):
        self.rsi_period = rsi_period
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.ma_period = ma_period

    def rsi(self, series):
        delta = series.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def check(self, df):
        if len(df) < self.rsi_period:
            return None

        df = df.copy()
        df['rsi'] = self.rsi(df['close'])
        df['ma'] = df['close'].rolling(self.ma_period).mean()

        last = df.iloc[-1]
        rsi_val = last['rsi']
        price = last['close']
        ma = last['ma']

        if np.isnan(rsi_val) or np.isnan(ma):
            return None

        deviation = (price - ma) / ma

        if rsi_val < self.rsi_low or deviation < -0.03:  # 放宽偏差阈值
            confidence = min(1.0, (self.rsi_low - rsi_val) / 20 + 0.5)
            return {
                "action": "buy",
                "confidence": round(confidence, 2)
            }
        elif rsi_val > self.rsi_high or deviation > 0.03:
            confidence = min(1.0, (rsi_val - self.rsi_high) / 20 + 0.5)
            return {
                "action": "sell",
                "confidence": round(confidence, 2)
            }

        return None