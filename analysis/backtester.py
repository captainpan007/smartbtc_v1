# analysis/backtester.py

import os
import pandas as pd
import matplotlib.pyplot as plt
from core.data_loader import load_historical_data
from core.signal_generator import SignalGenerator
from core.market_state import MarketStateIdentifier
from core.strategy_switcher import StrategySwitcher
from core.risk_manager import RiskManager
from core.execution.executor import BacktestExecutor
from utils.indicators import calculate_atr


class Backtester:
    def __init__(self, data_path, starting_balance=1000):
        self.data_path = data_path
        self.data = load_historical_data(data_path)
        self.balance = starting_balance
        self.market_state_identifier = MarketStateIdentifier()
        self.strategy_switcher = StrategySwitcher()
        self.signal_generator = SignalGenerator()
        self.risk_manager = RiskManager()
        self.executor = BacktestExecutor(starting_balance=starting_balance)
        self.logs = []

    def run(self):
        print("[Backtester] Running backtest...")

        for i in range(50, len(self.data)):
            window = self.data.iloc[:i].copy().reset_index(drop=True)
            current_price = window['close'].iloc[-1]

            # 1. 判断市场状态
            market_state = self.market_state_identifier.identify(window)
            strategy_name = self.strategy_switcher.select(market_state)

            # 2. 生成信号
            signal = self.signal_generator.generate(window, strategy_name)
            signal['strategy'] = strategy_name

            # 3. 动态止损计算（真实 ATR）
            atr = calculate_atr(window)
            stop_loss_distance = atr * 2
            signal['stop_loss'] = current_price - stop_loss_distance
            signal['take_profit'] = current_price + stop_loss_distance * 1.5

            # 4. 资金管理
            position_size = self.risk_manager.calculate_position_size(
                current_balance=self.executor.balance,
                stop_loss_distance=stop_loss_distance
            )
            signal['amount'] = position_size

            # 5. 执行交易
            execution_result = self.executor.execute(signal, current_price)
            if execution_result:
                self.logs.append(execution_result)

            # 6. 回撤控制
            if self.executor.max_drawdown_exceeded():
                print("[Backtester] ❌ Max drawdown exceeded. Stopping backtest.")
                break

        print("[Backtester] ✅ Completed.")
        self._visualize()

    def _visualize(self):
        balances = self.executor.get_balances()
        plt.figure(figsize=(10, 4))
        plt.plot(balances, label="Equity")
        plt.title("Backtest Equity Curve")
        plt.xlabel("Trade Index")
        plt.ylabel("Balance")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    backtester = Backtester(data_path="core/data/historical/BTCUSDT_4h.csv")
    backtester.run()
