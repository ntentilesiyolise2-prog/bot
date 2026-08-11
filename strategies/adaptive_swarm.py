import pandas as pd
import numpy as np
from collections import deque
from .trend import TrendStrategy
from .mean_reversion import MeanReversionStrategy
from .breakout import BreakoutStrategy
from .momentum import MomentumStrategy

class AdaptiveSwarm:
    def __init__(self, window=50):
        self.strategies = [
            TrendStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
            MomentumStrategy(),
        ]
        self.performance = {s.name: deque(maxlen=window) for s in self.strategies}
        self.weights = {s.name: 0.25 for s in self.strategies}
        self.window = window

    def update_performance(self, name, pnl):
        if name in self.performance:
            self.performance[name].append(pnl)

    def recalc_weights(self):
        total_sharpe = 0
        sharpe = {}
        for name, perf in self.performance.items():
            if len(perf) > 5:
                s = np.mean(perf) / (np.std(perf) + 1e-6)
                sharpe[name] = max(0, s)
                total_sharpe += sharpe[name]
        if total_sharpe > 0:
            for name in self.weights:
                self.weights[name] = sharpe.get(name, 0) / total_sharpe
        # Normalise
        total = sum(self.weights.values())
        if total > 0:
            for name in self.weights:
                self.weights[name] /= total

    def get_votes(self, df):
        votes = []
        for s in self.strategies:
            signal = s.get_signal(df)
            votes.append(signal)
        buy_weight = sum(self.weights[s.name] for s, v in zip(self.strategies, votes) if v == 'BUY')
        sell_weight = sum(self.weights[s.name] for s, v in zip(self.strategies, votes) if v == 'SELL')
        hold_weight = 1 - buy_weight - sell_weight

        direction = 'HOLD'
        if buy_weight > 0.5:
            direction = 'BUY'
        elif sell_weight > 0.5:
            direction = 'SELL'

        confluence = max(buy_weight, sell_weight) * 100
        return {
            'direction': direction,
            'confluence': round(confluence, 1),
            'votes': votes,
            'breakdown': {
                'buy': round(buy_weight * 100, 1),
                'sell': round(sell_weight * 100, 1),
                'hold': round(hold_weight * 100, 1)
            }
        }
