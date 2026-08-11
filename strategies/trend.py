from .base import BaseStrategy
import pandas as pd

class TrendStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("trend")

    def get_signal(self, df: pd.DataFrame) -> str:
        last = df.iloc[-1]
        if last['ema_9'] > last['ema_21'] and last['rsi_14'] > 50:
            return "BUY"
        elif last['ema_9'] < last['ema_21'] and last['rsi_14'] < 50:
            return "SELL"
        return "HOLD"
