from .trend import TrendStrategy
from .mean_reversion import MeanReversionStrategy
from .breakout import BreakoutStrategy
from .momentum import MomentumStrategy
import pandas as pd
from collections import Counter

class StrategySwarm:
    def __init__(self):
        self.strategies = [
            TrendStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
            MomentumStrategy(),
        ]

    def get_votes(self, df: pd.DataFrame) -> dict:
        votes = [s.get_signal(df) for s in self.strategies]
        counts = Counter(votes)
        # Compute confluence
        total = len(votes)
        buy_pct = counts.get("BUY", 0) / total
        sell_pct = counts.get("SELL", 0) / total
        hold_pct = counts.get("HOLD", 0) / total

        direction = "HOLD"
        if buy_pct > 0.5:
            direction = "BUY"
        elif sell_pct > 0.5:
            direction = "SELL"

        confluence = max(buy_pct, sell_pct) * 100
        return {
            "direction": direction,
            "confluence": round(confluence, 1),
            "votes": votes,
            "breakdown": {
                "buy": round(buy_pct * 100, 1),
                "sell": round(sell_pct * 100, 1),
                "hold": round(hold_pct * 100, 1)
            }
        }
