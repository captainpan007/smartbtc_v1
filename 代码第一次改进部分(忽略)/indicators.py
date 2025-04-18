# utils/indicators.py

import pandas as pd
import numpy as np

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

# 新增：K线形态识别函数
def detect_hammer(df):
    """识别锤头线形态：小实体，长下影线，出现在下跌趋势中"""
    if len(df) < 5:
        return False

    # 当前K线
    open_price = df['open'].iloc[-1]
    close_price = df['close'].iloc[-1]
    high_price = df['high'].iloc[-1]
    low_price = df['low'].iloc[-1]

    # 形态特征
    body = abs(close_price - open_price)
    lower_shadow = min(open_price, close_price) - low_price
    upper_shadow = high_price - max(open_price, close_price)

    # 锤头线条件：小实体，长下影线（>2倍实体），短上影线
    hammer_condition = (lower_shadow > 2 * body) and (upper_shadow < body) and (body > 0)

    # 上下文：前5根K线下跌（趋势确认）
    trend = df['close'].iloc[-5:-1].pct_change().sum()
    downtrend = trend < -0.02  # 前5根K线累计下跌>2%

    return hammer_condition and downtrend

def detect_engulfing(df):
    """识别吞没形态：第二根K线完全吞没第一根K线"""
    if len(df) < 2:
        return False, None

    # 前一根K线
    prev_open = df['open'].iloc[-2]
    prev_close = df['close'].iloc[-2]
    # 当前K线
    curr_open = df['open'].iloc[-1]
    curr_close = df['close'].iloc[-1]

    # 看涨吞没：前一根为阴线，当前为阳线，完全吞没前一根
    bullish_engulfing = (prev_close < prev_open) and (curr_close > curr_open) and \
                        (curr_open <= prev_close) and (curr_close >= prev_open)
    # 看跌吞没：前一根为阳线，当前为阴线，完全吞没前一根
    bearish_engulfing = (prev_close > prev_open) and (curr_close < curr_open) and \
                        (curr_open >= prev_close) and (curr_close <= prev_open)

    if bullish_engulfing:
        return True, "bullish"
    elif bearish_engulfing:
        return True, "bearish"
    return False, None

def detect_doji(df):
    """识别十字星形态：开盘价≈收盘价，实体很小"""
    open_price = df['open'].iloc[-1]
    close_price = df['close'].iloc[-1]
    body = abs(close_price - open_price)
    range = df['high'].iloc[-1] - df['low'].iloc[-1]

    # 十字星条件：实体<范围的5%
    doji_condition = (body < 0.05 * range) and (range > 0)
    return doji_condition

# 新增：条件概率分析
def calculate_pattern_probability(df, pattern_func, lookback=5):
    """计算K线形态后价格走势的概率"""
    if len(df) < lookback + 1:
        return 0, 0

    # 检测形态
    pattern_occurrences = []
    for i in range(len(df) - lookback):
        window = df.iloc[:i+1]
        if pattern_func(window):
            # 计算形态后lookback根K线的涨跌幅
            future_price = df['close'].iloc[i + lookback]
            current_price = df['close'].iloc[i]
            change = (future_price - current_price) / current_price
            pattern_occurrences.append(change)

    if not pattern_occurrences:
        return 0, 0

    # 计算上涨概率
    up_prob = sum(1 for x in pattern_occurrences if x > 0) / len(pattern_occurrences)
    avg_change = np.mean(pattern_occurrences)
    return up_prob, avg_change