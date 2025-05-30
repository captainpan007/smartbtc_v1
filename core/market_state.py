# core/market_state.py

import pandas as pd
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange
from utils.indicators import calculate_bollinger_bands

class MarketStateDetector:
    def __init__(self, adx_threshold=30, atr_window=14):
        self.adx_threshold = adx_threshold
        self.atr_window = atr_window

    def detect_state(self, df: pd.DataFrame) -> str:
        if len(df) < self.atr_window + 10:
            return "unknown"

        try:
            # ADX计算
            adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14).adx()
            latest_adx = adx.iloc[-1]

            # ATR计算
            atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=self.atr_window).average_true_range()
            latest_atr = atr.iloc[-1]
            close_price = df['close'].iloc[-1]
            atr_ratio = latest_atr / close_price

            # 布林带宽度
            df = calculate_bollinger_bands(df, window=20)
            bb_width = (df['upper'] - df['lower']) / df['ma']
            avg_bb_width = bb_width[-20:-1].mean()
            current_bb_width = bb_width.iloc[-1]

            # 成交量分析
            avg_volume = df['volume'].iloc[-20:-1].mean()
            current_volume = df['volume'].iloc[-1]
            volume_spike = current_volume > 2 * avg_volume

            # 波动率和成交量趋势
            volatility = df['close'].rolling(20).std().iloc[-1]
            avg_volatility = df['close'].rolling(20).std()[-20:-1].mean()
            volume_trend = (current_volume - df['volume'].iloc[-5]) / df['volume'].iloc[-5]

            # 综合判断
            adx_weight = 0.3
            atr_weight = 0.2
            bb_weight = 0.2
            volume_weight = 0.1
            volatility_weight = 0.1
            volume_trend_weight = 0.1
            trend_score = (adx_weight * (latest_adx / 100) +
                          atr_weight * (atr_ratio / 0.02) +
                          bb_weight * (current_bb_width / avg_bb_width) +
                          volume_weight * (1 if volume_spike else 0) +
                          volatility_weight * (volatility / avg_volatility) +
                          volume_trend_weight * max(0, volume_trend))

            if trend_score > 0.7:
                return "trending"
            elif trend_score < 0.005:
                return "ranging"
            else:
                return "neutral"
        except Exception as e:
            print(f"[MarketStateDetector] Error: {e}")
            return "unknown"