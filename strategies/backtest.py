import backtesting as bt
import pandas as pd

class SlippageBacktest(bt.Strategy):
    def init(self):
        self.spread = 0.0001  # 0.1 pip for FX
        self.slippage = 0.00005

    def next(self):
        price = self.data.Close[-1]
        # Simulate market order with spread and slippage
        buy_price = price + self.spread/2 + self.slippage
        sell_price = price - self.spread/2 - self.slippage
        # Your logic to enter/exit using these adjusted prices
