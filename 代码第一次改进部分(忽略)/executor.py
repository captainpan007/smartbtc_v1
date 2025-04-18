# core/executor.py

from core.config_loader import load_config
from ta.volatility import AverageTrueRange

class TradeExecutor:
    def __init__(self, simulate=False, df=None):
        self.simulate = simulate
        self.df = df
        config = load_config()
        self.api_key = config["binance"]["api_key"]
        self.api_secret = config["binance"]["api_secret"]
        self.commission_rate = 0.00075
        self.base_slippage_rate = 0.00005
        self.holdings = 0  # 持仓数量
        self.entry_price = 0  # 买入价格
        self.entry_commission = 0  # 买入手续费
        self.entry_slippage = 0  # 买入滑点

    def calculate_dynamic_slippage(self, price):
        if self.df is None:
            return price * self.base_slippage_rate

        atr = AverageTrueRange(high=self.df['high'], low=self.df['low'], close=self.df['close'], window=14).average_true_range()
        latest_atr = atr.iloc[-1]
        atr_ratio = latest_atr / price

        if atr_ratio > 0.02:
            slippage_rate = self.base_slippage_rate * 2
        elif atr_ratio < 0.005:
            slippage_rate = self.base_slippage_rate * 0.5
        else:
            slippage_rate = self.base_slippage_rate
        return price * slippage_rate

    def execute(self, order):
        if self.simulate:
            return self._simulate_order(order)
        else:
            return self._real_order(order)

    def _simulate_order(self, order):
        price = order["price"]
        amount = order["amount"]

        # 计算动态滑点和手续费
        slippage = self.calculate_dynamic_slippage(price)
        adjusted_price = price + slippage if order["action"] == "buy" else price - slippage
        commission = amount * adjusted_price * self.commission_rate

        # 计算盈亏
        pnl = 0
        if order["action"] == "buy":
            self.holdings += amount
            self.entry_price = adjusted_price
            self.entry_commission = commission
            self.entry_slippage = slippage
        elif order["action"] == "sell" and self.holdings > 0:
            self.holdings -= amount
            exit_commission = commission
            exit_slippage = slippage
            # 盈亏 = (卖出价格 - 买入价格) × 数量 - (买入手续费 + 卖出手续费 + 买入滑点 + 卖出滑点)
            pnl = (adjusted_price - self.entry_price) * amount - (self.entry_commission + exit_commission + self.entry_slippage + exit_slippage)
            self.entry_price = 0
            self.entry_commission = 0
            self.entry_slippage = 0

        print(f"[Simulated] {order['action'].upper()} {amount} {order['symbol']} @ {adjusted_price} (原价: {price}, 滑点: {slippage}, 手续费: {commission}, 盈亏: {pnl}) 结构={order['structure']}")

        return {
            "symbol": order["symbol"],
            "action": order["action"],
            "price": adjusted_price,
            "amount": amount,
            "commission": commission,
            "slippage": slippage,
            "pnl": pnl,  # 新增盈亏字段
            "timestamp": order["timestamp"],
            "structure": order["structure"],
            "regime": order.get("regime", "unknown")
        }

    def _real_order(self, order):
        price = order["price"]
        amount = order["amount"]
        slippage = self.calculate_dynamic_slippage(price)
        limit_price = price + slippage if order["action"] == "buy" else price - slippage

        commission = amount * limit_price * self.commission_rate

        # 计算盈亏
        pnl = 0
        if order["action"] == "buy":
            self.holdings += amount
            self.entry_price = limit_price
            self.entry_commission = commission
            self.entry_slippage = slippage
        elif order["action"] == "sell" and self.holdings > 0:
            self.holdings -= amount
            exit_commission = commission
            exit_slippage = slippage
            pnl = (limit_price - self.entry_price) * amount - (self.entry_commission + exit_commission + self.entry_slippage + exit_slippage)
            self.entry_price = 0
            self.entry_commission = 0
            self.entry_slippage = 0

        print(f"[REAL] 提交限价单：{order['action'].upper()} {amount} {order['symbol']} @ {limit_price}")

        return {
            "symbol": order["symbol"],
            "action": order["action"],
            "price": limit_price,
            "amount": amount,
            "commission": commission,
            "slippage": slippage,
            "pnl": pnl,  # 新增盈亏字段
            "timestamp": order["timestamp"],
            "structure": order["structure"],
            "regime": order.get("regime", "unknown")
        }