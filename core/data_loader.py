# core/data_loader.py

class MarketDataLoader:
    def __init__(self, symbol="BTC/USDT", timeframe="4h", limit=1000):
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.data_path = "core/data/historical/BTCUSDT_4h.csv"  # 默认路径

    def get_ohlcv(self):
        import pandas as pd
        df = pd.read_csv(self.data_path)
        if len(df) < 100:
            print(f"[DataLoader] 警告：数据量不足，仅有 {len(df)} 条数据")
            return None
        return df
    