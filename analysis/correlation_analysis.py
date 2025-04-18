# analysis/correlation_analysis.py

import pandas as pd
import numpy as np

class CorrelationAnalysis:
    def __init__(self, data_path="core/data/historical/BTCUSDT_4h.csv"):
        self.data_path = data_path
        self.df = None

    def load_data(self):
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

    def calculate_indicators(self):
        """计算策略指标和预测结果"""
        if self.df is None:
            self.load_data()

        # 技术指标
        from utils.indicators import calculate_rsi, calculate_bollinger_bands, calculate_adx
        self.df['rsi'] = calculate_rsi(self.df['close'], window=14)
        self.df = calculate_bollinger_bands(self.df, window=20)
        self.df['bb_width'] = (self.df['upper'] - self.df['lower']) / self.df['ma']
        self.df['adx'] = calculate_adx(self.df)

        # 情绪数据（示例，需替换为真实数据）
        from core.data_loader import MarketDataLoader
        loader = MarketDataLoader()
        fg_data = loader.get_fear_greed()
        self.df['fg_index'] = fg_data.get("value", 50)

        # 链上数据（示例，需替换为真实数据）
        onchain = loader.get_onchain_metrics()
        self.df['exchange_volume'] = onchain.get("exchange_volume", 50000)

        # 预测结果：未来5根K线的涨跌幅
        self.df['future_return'] = self.df['close'].shift(-5) / self.df['close'] - 1

    def compute_correlations(self):
        """计算皮尔逊和斯皮尔曼相关系数"""
        if self.df is None:
            self.calculate_indicators()

        indicators = ['rsi', 'bb_width', 'adx', 'fg_index', 'exchange_volume']
        target = 'future_return'

        data = self.df[indicators + [target]].dropna()

        pearson_corr = data.corr(method='pearson')[target]
        spearman_corr = data.corr(method='spearman')[target]

        return pearson_corr, spearman_corr

    def run_analysis(self):
        pearson_corr, spearman_corr = self.compute_correlations()
        print("\n📊 Correlation Analysis Results:")
        print("\nPearson Correlation (Linear):")
        for indicator, value in pearson_corr.items():
            if indicator != 'future_return':
                print(f"{indicator}: {value:.3f}")
        print("\nSpearman Correlation (Monotonic):")
        for indicator, value in spearman_corr.items():
            if indicator != 'future_return':
                print(f"{indicator}: {value:.3f}")

if __name__ == "__main__":
    analysis = CorrelationAnalysis()
    analysis.run_analysis()