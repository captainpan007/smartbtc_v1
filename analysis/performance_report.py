# analysis/performance_report.py

import pandas as pd
import matplotlib.pyplot as plt
import os

class PerformanceReport:
    def __init__(self, log_path="logs/trade_log.csv"):
        self.log_path = log_path
        self.df = None

    def load_data(self):
        if not os.path.exists(self.log_path):
            raise FileNotFoundError(f"[Error] Log file not found: {self.log_path}")
        self.df = pd.read_csv(self.log_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

    def compute_metrics(self):
        if self.df is None:
            self.load_data()

        trades = self.df[self.df['action'].isin(['buy', 'sell'])].copy()
        trades['pnl'] = trades['pnl'].fillna(0)

        win_trades = trades[trades['pnl'] > 0]
        loss_trades = trades[trades['pnl'] < 0]

        winrate = len(win_trades) / len(trades) * 100 if len(trades) > 0 else 0
        avg_win = win_trades['pnl'].mean() if not win_trades.empty else 0
        avg_loss = loss_trades['pnl'].mean() if not loss_trades.empty else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        net_profit = trades['pnl'].sum()

        return {
            "Total Trades": len(trades),
            "Win Rate": round(winrate, 2),
            "Avg Win": round(avg_win, 2),
            "Avg Loss": round(avg_loss, 2),
            "Profit Factor": round(profit_factor, 2),
            "Net Profit": round(net_profit, 2)
        }

    def plot_pnl_curve(self):
        if self.df is None:
            self.load_data()
        self.df['cumulative_pnl'] = self.df['pnl'].fillna(0).cumsum()

        plt.figure(figsize=(10, 5))
        plt.plot(self.df['timestamp'], self.df['cumulative_pnl'], label="Cumulative PnL")
        plt.title("Cumulative PnL Over Time")
        plt.xlabel("Time")
        plt.ylabel("PnL (USDT)")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def plot_win_loss_distribution(self):
        if self.df is None:
            self.load_data()

        pnl = self.df['pnl'].dropna()
        plt.figure(figsize=(8, 4))
        plt.hist(pnl, bins=30, color='steelblue', edgecolor='black')
        plt.title("PnL Distribution")
        plt.xlabel("Profit / Loss")
        plt.ylabel("Frequency")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def run_report(self):
        metrics = self.compute_metrics()
        print("\n📊 Performance Summary:")
        for k, v in metrics.items():
            print(f"{k}: {v}")
        self.plot_pnl_curve()
        self.plot_win_loss_distribution()
