# core/signal_generator.py

import pandas as pd
from strategies.mean_reversion import MeanReversionStrategy
from strategies.trend_following import TrendFollowStrategy
from utils.indicators import calculate_rsi, calculate_bollinger_bands, calculate_adx
from utils.indicators import detect_hammer, detect_engulfing, detect_doji, calculate_pattern_probability, calc_macd, calc_stochrsi
from core.market_state import MarketStateDetector
from core.data_loader import MarketDataLoader
from .ai_model import AIPredictor

class SignalGenerator:
    def __init__(self, config):
        self.config = config
        self.rsi_period = config.get("signal_generator", {}).get("rsi_period", 14)
        self.mean_reversion = MeanReversionStrategy()
        self.trend_following = TrendFollowStrategy()
        self.market_state = MarketStateDetector()
        self.loader = MarketDataLoader(symbol="BTC/USDT", timeframe="4h", limit=1000)
        self.predictor = AIPredictor()
        self.weights = {
            'rsi': 0.16,
            'bb_width': 0.14,
            'adx': 0.12,
            'volume_change': 0.12,
            'macd': 0.11,
            'stoch_rsi': 0.10,
            'trend': 0.10,
            'hammer_up_prob': 0.08,
            'engulfing_up_prob': 0.08
        }

    def generate(self, df: pd.DataFrame) -> dict:
        signals = []

        # 技术指标计算
        df = df.copy()
        df['rsi'] = calculate_rsi(df['close'], window=14)
        df = calculate_bollinger_bands(df, window=20)
        df['bb_width'] = (df['upper'] - df['lower']) / df['ma']
        df['adx'] = calculate_adx(df)
        df['volume_change'] = df['volume'] / df['volume'].shift(1)
        df['macd'], df['macd_signal'], df['macd_hist'] = calc_macd(df['close'])
        df['stoch_rsi'] = calc_stochrsi(df['close'])
        df['hammer_up_prob'], _ = calculate_pattern_probability(df, detect_hammer, lookback=5)
        df['doji_up_prob'], _ = calculate_pattern_probability(df, detect_doji, lookback=5)
        df['engulfing_up_prob'], _ = calculate_pattern_probability(df, lambda d: detect_engulfing(d)[0] and detect_engulfing(d)[1] == "bullish", lookback=5)
        df['engulfing_down_prob'], _ = calculate_pattern_probability(df, lambda d: detect_engulfing(d)[0] and detect_engulfing(d)[1] == "bearish", lookback=5)
        df['trend'] = df['close'].pct_change(5).shift(1)
        df['volume_trend'] = df['volume'].pct_change(5).shift(1)
        df['volatility'] = df['close'].rolling(20).std()
        df['price_range'] = (df['high'] - df['low']) / df['close']

        # 市场状态识别
        market_condition = self.market_state.detect_state(df)
        print(f"[SignalGenerator] Market Condition: {market_condition}")

        # 打印调试信息
        print(f"[SignalGenerator] Exchange Volume: Removed")
        print(f"[SignalGenerator] Active Addresses: Removed")

        # K线形态识别和条件概率分析
        is_hammer = detect_hammer(df)
        is_doji = detect_doji(df)
        is_engulfing, engulfing_type = detect_engulfing(df)

        hammer_up_prob, _ = calculate_pattern_probability(df, detect_hammer, lookback=5)
        doji_up_prob, _ = calculate_pattern_probability(df, detect_doji, lookback=5)
        engulfing_up_prob, _ = calculate_pattern_probability(df, lambda d: detect_engulfing(d)[0] and detect_engulfing(d)[1] == "bullish", lookback=5)
        engulfing_down_prob, _ = calculate_pattern_probability(df, lambda d: detect_engulfing(d)[0] and detect_engulfing(d)[1] == "bearish", lookback=5)

        print(f"[SignalGenerator] K-Line Patterns - Hammer: {is_hammer}, Doji: {is_doji}, Engulfing: {is_engulfing} ({engulfing_type})")
        print(f"[SignalGenerator] Probabilities - Hammer Up: {hammer_up_prob:.2f}, Doji Up: {doji_up_prob:.2f}, Engulfing Up: {engulfing_up_prob:.2f}, Engulfing Down: {engulfing_down_prob:.2f}")

        trend = df['close'].iloc[-5:-1].pct_change().sum()
        downtrend = trend < -0.02
        uptrend = trend > 0.02
        avg_volume = df['volume'].iloc[-20:-1].mean()
        current_volume = df['volume'].iloc[-1]
        volume_spike = current_volume > 1.1 * avg_volume

        # 策略信号生成
        strategy_type = "trend_following"
        signal_data = self.trend_following.check(df)

        if market_condition == "ranging":
            strategy_type = "mean_reversion"
            signal_data = self.mean_reversion.check(df)

        # 信号增强：K线形态、AI模型预测
        if signal_data and isinstance(signal_data, dict) and "action" in signal_data:
            action = signal_data["action"]

            # 形态增强
            pattern_confidence = 0.0
            if action == "buy":
                if is_hammer and downtrend and volume_spike and hammer_up_prob > 0.1:
                    pattern_confidence = 0.4
                elif is_doji and downtrend and volume_spike and doji_up_prob > 0.1:
                    pattern_confidence = 0.2
            elif action == "sell":
                if is_engulfing and engulfing_type == "bearish" and uptrend and volume_spike and engulfing_down_prob > 0.4:
                    pattern_confidence = 0.4

            # 成交量增强
            volume_confidence = 0.0
            if volume_spike:
                volume_confidence = self.weights['volume_change']

            # AI模型预测
            # core/signal_generator.py (部分代码)

            # AI模型预测（移到 signal_data 检查之前）
            ai_prediction, ai_confidence = self.predictor.predict(df)
            print(f"[SignalGenerator] AI Prediction: {ai_prediction}, Confidence: {ai_confidence:.2f}")

            # 策略信号生成
            strategy_type = "trend_following"
            signal_data = self.trend_following.check(df)

            if market_condition == "ranging":
                strategy_type = "mean_reversion"
                signal_data = self.mean_reversion.check(df)

            # 信号增强
            if signal_data and isinstance(signal_data, dict) and "action" in signal_data:
                action = signal_data["action"]
                # 形态增强
                pattern_confidence = 0.0
                if action == "buy":
                    if is_hammer and downtrend and volume_spike and hammer_up_prob > 0.1:
                        pattern_confidence = 0.4
                    elif is_doji and downtrend and volume_spike and doji_up_prob > 0.1:
                        pattern_confidence = 0.2
                elif action == "sell":
                    if is_engulfing and engulfing_type == "bearish" and uptrend and volume_spike and engulfing_down_prob > 0.1:
                        pattern_confidence = 0.4

                # 成交量增强
                volume_confidence = 0.0
                if volume_spike:
                    volume_confidence = self.weights['volume_change']

                # 综合置信度
                if (ai_prediction == 1 and action == "buy") or (ai_prediction == 0 and action == "sell"):
                    total_confidence = ai_confidence + pattern_confidence + volume_confidence
                else:
                    total_confidence = pattern_confidence + volume_confidence

                print(f"[SignalGenerator] Total Confidence: {total_confidence:.2f}")
                if total_confidence < 0.2:
                    return None
            else:
                print(f"[SignalGenerator] No signal generated by strategy: {strategy_type}")
                return None

            signal = {
                "symbol": "BTC/USDT",
                "action": action,
                "confidence": round(total_confidence, 2),
                "structure": strategy_type,
                "meta": {
                    "rsi": df["rsi"].iloc[-1],
                    "adx": df["adx"].iloc[-1],
                    "volume_change": df["volume_change"].iloc[-1],
                    "hammer_detected": is_hammer,
                    "doji_detected": is_doji,
                    "engulfing_detected": is_engulfing,
                    "engulfing_type": engulfing_type,
                    "ai_prediction": int(ai_prediction),
                    "ai_confidence": ai_confidence
                }
            }
            signals.append(signal)

        return signals[0] if signals else None