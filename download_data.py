# download_data.py

import ccxt
import pandas as pd
import time
from datetime import datetime

def fetch_ohlcv(symbol='BTC/USDT', timeframe='4h', since=None, limit=1000):
    exchange = ccxt.binance()
    if since:
        since = exchange.parse8601(since)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def save_data(df, filename):
    df.to_csv(filename, index=False)

if __name__ == "__main__":
    start_date = '2023-01-01T00:00:00Z'
    end_date = '2024-01-01T00:00:00Z'
    limit = 1000

    all_data = []
    current_time = start_date

    while True:
        print(f"Fetching data from {current_time}...")
        df = fetch_ohlcv(since=current_time, limit=limit)
        if not df.empty:
            all_data.append(df)
            last_timestamp = df['timestamp'].iloc[-1]
            end_date_dt = pd.to_datetime(end_date).tz_localize(None)  # 移除时区信息
            if last_timestamp >= end_date_dt:
                break
            current_time = last_timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
            time.sleep(1)
        else:
            break

    full_df = pd.concat(all_data, ignore_index=True)
    full_df = full_df.drop_duplicates(subset=['timestamp'])
    save_data(full_df, 'core/data/historical/BTCUSDT_4h_new.csv')
    print(f"Data saved to core/data/historical/BTCUSDT_4h_new.csv")