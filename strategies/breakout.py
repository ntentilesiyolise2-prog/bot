from .base import BaseStrategy
import pandas as pd

class BreakoutStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("breakout")

    def get_signal(self, df: pd.DataFrame) -> str:
        last = df.iloc[-1]
        # 20-day high/low breakout
        high_20 = df['High'].rolling(20).max().iloc[-1]
        low_20 = df['Low'].rolling(20).min().iloc[-1]
        if last['Close'] > high_20 and last['volume'] > df['Volume'].rolling(20).mean().iloc[-1]:
            return "BUY"
        elif last['Close'] < low_20 and last['volume'] > df['Volume'].rolling(20).mean().iloc[-1]:
            return "SELL"
        return "HOLD"
