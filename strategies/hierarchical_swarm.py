import pandas as pd
import numpy as np
from collections import deque
from .trend import TrendStrategy
from .mean_reversion import MeanReversionStrategy
from .breakout import BreakoutStrategy
from .momentum import MomentumStrategy
from utils.logger import setup_logger

logger = setup_logger(__name__)

class HierarchicalSwarm:
    def __init__(self, window=50):
        self.scalp_strategies = [MomentumStrategy(), MeanReversionStrategy()]
        self.day_strategies = [TrendStrategy(), BreakoutStrategy()]
        self.swing_strategies = [TrendStrategy(), MeanReversionStrategy()]
        self.position_strategies = [TrendStrategy()]

        self.performance = {
            'scalp': deque(maxlen=window),
            'day': deque(maxlen=window),
            'swing': deque(maxlen=window),
            'position': deque(maxlen=window)
        }
        self.weights = self._load_weights()
        self.regime = 'neutral'
        self.last_update = None

    def _load_weights(self):
        try:
            import json
            with open('strategy_weights.json', 'r') as f:
                return json.load(f)
        except:
            return {'scalp': 0.25, 'day': 0.35, 'swing': 0.25, 'position': 0.15}

    def _save_weights(self):
        import json
        with open('strategy_weights.json', 'w') as f:
            json.dump(self.weights, f, indent=4)

    def update_performance(self, layer, pnl):
        if layer in self.performance:
            self.performance[layer].append(pnl)

    def recalc_weights(self):
        total_sharpe = 0
        sharpe = {}
        for layer, perf in self.performance.items():
            if len(perf) > 5:
                s = np.mean(perf) / (np.std(perf) + 1e-6)
                sharpe[layer] = max(0, s)
                total_sharpe += sharpe[layer]
        if total_sharpe > 0:
            for layer in self.weights:
                self.weights[layer] = sharpe.get(layer, 0) / total_sharpe
        total = sum(self.weights.values())
        if total > 0:
            for layer in self.weights:
                self.weights[layer] /= total
        self._save_weights()

    def set_regime(self, regime):
        self.regime = regime
        # Adjust weights based on regime
        if regime == 'trending':
            self.weights['day'] *= 1.2
            self.weights['swing'] *= 1.2
        elif regime == 'choppy':
            self.weights['scalp'] *= 1.3
            self.weights['day'] *= 0.7
        elif regime == 'volatile':
            self.weights['scalp'] *= 0.6
            self.weights['day'] *= 0.8
        # Normalize
        total = sum(self.weights.values())
        if total > 0:
            for layer in self.weights:
                self.weights[layer] /= total

    def get_votes(self, df):
        scalp_votes = [s.get_signal(df) for s in self.scalp_strategies]
        day_votes = [s.get_signal(df) for s in self.day_strategies]
        swing_votes = [s.get_signal(df) for s in self.swing_strategies]
        position_votes = [s.get_signal(df) for s in self.position_strategies]

        buy_weight = 0
        sell_weight = 0
        layers = {
            'scalp': scalp_votes,
            'day': day_votes,
            'swing': swing_votes,
            'position': position_votes
        }
        for layer, votes in layers.items():
            w = self.weights[layer]
            buy_count = sum(1 for v in votes if v == 'BUY')
            sell_count = sum(1 for v in votes if v == 'SELL')
            total = len(votes)
            if total > 0:
                buy_weight += (buy_count / total) * w
                sell_weight += (sell_count / total) * w

        direction = 'HOLD'
        if buy_weight > 0.5:
            direction = 'BUY'
        elif sell_weight > 0.5:
            direction = 'SELL'

        confluence = max(buy_weight, sell_weight) * 100

        return {
            'direction': direction,
            'confluence': round(confluence, 1),
            'votes': list(layers.values()),
            'breakdown': {
                'buy': round(buy_weight * 100, 1),
                'sell': round(sell_weight * 100, 1),
                'hold': round((1 - buy_weight - sell_weight) * 100, 1)
            }
        }
