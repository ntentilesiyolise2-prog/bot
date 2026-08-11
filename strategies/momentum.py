from .base import BaseStrategy
import pandas as pd

class MomentumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("momentum")

    def get_signal(self, df: pd.DataFrame) -> str:
        last = df.iloc[-1]
        # MACD crossover
        if last['macd'] > last['macd_signal'] and last['macd_hist'] > 0:
            return "BUY"
        elif last['macd'] < last['macd_signal'] and last['macd_hist'] < 0:
            return "SELL"
        return "HOLD"
