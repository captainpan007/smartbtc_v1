# split_data.py

import pandas as pd

def split_data(input_file, output_prefix, split_size=730):
    df = pd.read_csv(input_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    total_rows = len(df)
    num_splits = (total_rows + split_size - 1) // split_size

    for i in range(num_splits):
        start_idx = i * split_size
        end_idx = min((i + 1) * split_size, total_rows)
        split_df = df.iloc[start_idx:end_idx]
        split_df.to_csv(f"{output_prefix}_part_{i+1}.csv", index=False)
        print(f"Saved {output_prefix}_part_{i+1}.csv with {len(split_df)} rows")

if __name__ == "__main__":
    input_file = "core/data/historical/BTCUSDT_4h_new.csv"
    output_prefix = "core/data/historical/BTCUSDT_4h_split"
    split_data(input_file, output_prefix)