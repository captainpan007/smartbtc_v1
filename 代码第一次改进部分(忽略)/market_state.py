# core/market_state.py

import pandas as pd
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange
from utils.indicators import calculate_bollinger_bands

class MarketStateDetector:
    def __init__(self, adx_threshold=25, atr_window=14):
        self.adx_threshold = adx_threshold
        self.atr_window = atr_window

    def detect_state(self, df: pd.DataFrame) -> str:
        """
        输入：包含 ['high', 'low', 'close', 'volume'] 列的 DataFrame
        输出："trending" 或 "ranging"
        """
        if len(df) < self.atr_window + 10:
            return "unknown"  # 数据不足

        try:
            # ADX计算
            adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14).adx()
            latest_adx = adx.iloc[-1]

            # ATR计算
            atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=self.atr_window).average_true_range()
            latest_atr = atr.iloc[-1]
            close_price = df['close'].iloc[-1]
            atr_ratio = latest_atr / close_price  # 用于辅助判断波动率

            # 布林带宽度
            df = calculate_bollinger_bands(df, window=20)
            bb_width = (df['upper'] - df['lower']) / df['ma']
            avg_bb_width = bb_width[-20:-1].mean()  # 前20根K线平均宽度
            current_bb_width = bb_width.iloc[-1]

            # 成交量分析
            avg_volume = df['volume'].iloc[-20:-1].mean()  # 前20根K线平均成交量
            current_volume = df['volume'].iloc[-1]
            volume_spike = current_volume > 1.5 * avg_volume

            # 综合判断
            if latest_adx >= self.adx_threshold and atr_ratio > 0.01 and current_bb_width > avg_bb_width and volume_spike:
                return "trending"
            elif latest_adx < self.adx_threshold and atr_ratio < 0.008 and current_bb_width < avg_bb_width:
                return "ranging"
            else:
                return "neutral"
        except Exception as e:
            print(f"[MarketStateDetector] Error: {e}")
            return "unknown"