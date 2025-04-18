# core/signal_generator.py

import pandas as pd
from strategies.mean_reversion import MeanReversionStrategy
from strategies.trend_following import TrendFollowStrategy
from utils.indicators import calculate_rsi, calculate_bollinger_bands, calculate_adx
from utils.indicators import detect_hammer, detect_engulfing, detect_doji, calculate_pattern_probability
from core.market_state import MarketStateDetector
from core.data_loader import MarketDataLoader

class SignalGenerator:
    def __init__(self):
        self.mean_reversion = MeanReversionStrategy()
        self.trend_following = TrendFollowStrategy()
        self.market_state = MarketStateDetector()
        self.loader = MarketDataLoader(symbol="BTC/USDT", timeframe="4h", limit=200)

    def generate(self, df: pd.DataFrame) -> dict:
        signals = []

        # ========== 1. 技术指标计算 ==========
        df = df.copy()
        df['rsi'] = calculate_rsi(df['close'], window=14)
        df = calculate_bollinger_bands(df, window=20)
        df['adx'] = calculate_adx(df)

        # ========== 2. 市场状态识别 ==========
        market_condition = self.market_state.detect_state(df)

        # ========== 3. 情绪指标 ==========
        fear_greed = self.loader.get_fear_greed()
        fg_level = int(fear_greed.get("value", 50))

        # ========== 4. 链上数据指标 ==========
        onchain = self.loader.get_onchain_metrics()
        active_addresses = onchain.get("active_addresses", 0)
        exchange_volume = onchain.get("exchange_volume", 0)

        # ========== 5. K线形态识别和条件概率分析 ==========
        # 检测形态
        is_hammer = detect_hammer(df)
        is_doji = detect_doji(df)
        is_engulfing, engulfing_type = detect_engulfing(df)

        # 计算形态后价格走势概率（未来5根K线）
        hammer_up_prob, _ = calculate_pattern_probability(df, detect_hammer, lookback=5)
        doji_up_prob, _ = calculate_pattern_probability(df, detect_doji, lookback=5)
        engulfing_up_prob, _ = calculate_pattern_probability(df, lambda d: detect_engulfing(d)[0] and detect_engulfing(d)[1] == "bullish", lookback=5)
        engulfing_down_prob, _ = calculate_pattern_probability(df, lambda d: detect_engulfing(d)[0] and detect_engulfing(d)[1] == "bearish", lookback=5)

        # 上下文分析：趋势和成交量
        trend = df['close'].iloc[-5:-1].pct_change().sum()  # 前5根K线涨跌幅
        downtrend = trend < -0.02  # 下跌>2%
        uptrend = trend > 0.02    # 上涨>2%
        avg_volume = df['volume'].iloc[-20:-1].mean()  # 前20根K线平均成交量
        current_volume = df['volume'].iloc[-1]
        volume_spike = current_volume > 1.5 * avg_volume  # 成交量>均值1.5倍

        # ========== 6. 策略信号生成 ==========
        strategy_type = "trend_following"
        signal_data = self.trend_following.check(df)

        if market_condition == "ranging":
            strategy_type = "mean_reversion"
            signal_data = self.mean_reversion.check(df)

        # ========== 7. 信号增强：K线形态、情绪和链上数据 ==========
        if signal_data and isinstance(signal_data, dict) and "action" in signal_data:
            action = signal_data["action"]
            base_confidence = signal_data.get("confidence", 0.5)

            # 形态增强
            pattern_confidence = 0.0
            if action == "buy":
                if is_hammer and downtrend and volume_spike and hammer_up_prob > 0.6:
                    pattern_confidence = 0.3
                elif is_doji and downtrend and volume_spike and doji_up_prob > 0.6:
                    pattern_confidence = 0.2
            elif action == "sell":
                if is_engulfing and engulfing_type == "bearish" and uptrend and volume_spike and engulfing_down_prob > 0.6:
                    pattern_confidence = 0.3

            # 情绪增强
            fg_confidence = 0.0
            if action == "buy" and fg_level < 25:
                fg_confidence = 0.2
            elif action == "sell" and fg_level > 75:
                fg_confidence = 0.2

            # 链上数据增强
            onchain_confidence = 0.0
            avg_exchange_volume = 50000  # 假设历史均值（需替换为真实数据）
            if action == "buy" and exchange_volume > 1.5 * avg_exchange_volume:
                onchain_confidence = 0.1
            elif action == "sell" and exchange_volume > 1.5 * avg_exchange_volume:
                onchain_confidence = 0.1

            # 综合置信度
            total_confidence = base_confidence + pattern_confidence + fg_confidence + onchain_confidence
            if total_confidence < 0.7:  # 仅触发置信度>0.7的信号
                return None

            signal = {
                "symbol": "BTC/USDT",
                "action": action,
                "confidence": round(total_confidence, 2),
                "structure": strategy_type,
                "meta": {
                    "rsi": df["rsi"].iloc[-1],
                    "adx": df["adx"].iloc[-1],
                    "fg_index": fg_level,
                    "onchain_active": active_addresses,
                    "onchain_volume": exchange_volume,
                    "hammer_detected": is_hammer,
                    "doji_detected": is_doji,
                    "engulfing_detected": is_engulfing,
                    "engulfing_type": engulfing_type
                }
            }
            signals.append(signal)

        return signals[0] if signals else None