from .base import BaseStrategy
import pandas as pd

class MeanReversionStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("mean_reversion")

    def get_signal(self, df: pd.DataFrame) -> str:
        last = df.iloc[-1]
        # If price is below the lower Bollinger Band and RSI < 30 -> BUY
        if last['rsi_14'] < 30 and last['Close'] < last['bb_low']:
            return "BUY"
        # If price is above the upper Bollinger Band and RSI > 70 -> SELL
        elif last['rsi_14'] > 70 and last['Close'] > last['bb_high']:
            return "SELL"
        return "HOLD"
