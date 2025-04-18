# core/strategy_switcher.py

from core.market_state import MarketStateDetector
from strategies.mean_reversion import MeanReversionStrategy
from strategies.trend_following import TrendFollowStrategy

class StrategySwitcher:
    def __init__(self):
        self.market_state_detector = MarketStateDetector()
        self.mean_reversion = MeanReversionStrategy()
        self.trend_following = TrendFollowStrategy()
        self.previous_state = "neutral"  # 记录上一次状态

    def select(self, df):
        """
        根据市场状态选择对应策略实例
        """
        state = self.market_state_detector.detect_state(df)

        # 引入过渡状态，减少频繁切换
        if state == "neutral":
            print("⏸ 市场状态过渡 → 使用上一次策略")
            if self.previous_state == "ranging":
                return self.mean_reversion
            elif self.previous_state == "trending":
                return self.trend_following
            else:
                return None

        self.previous_state = state
        if state == "ranging":
            print("📉 市场震荡 → 启用均值回归策略")
            return self.mean_reversion
        elif state == "trending":
            print("📈 市场趋势 → 启用趋势跟踪策略")
            return self.trend_following
        else:
            print("⏸ 市场状态未知 → 不生成信号")
            return None
        
        