import ccxt
import pandas as pd

# 初始化 Binance
exchange = ccxt.binance()

# 参数设置
symbol = "BTC/USDT"
timeframe = "4h"
limit = 1000  # 可修改为更大，如1500

# 获取数据
ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

# 转换为 DataFrame
df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

# 保存路径（你的项目中指定位置）
save_path = r"F:\量化交易算法\smartbtc_v1\core\data\historical\BTCUSDT_4h.csv"
df.to_csv(save_path, index=False)

print(f"✅ 数据已保存到：{save_path}")
