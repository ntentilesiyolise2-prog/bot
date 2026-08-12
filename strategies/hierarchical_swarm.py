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
        # Layer 1: Scalping (M1)
        self.scalp_strategies = [MomentumStrategy(), MeanReversionStrategy()]
        # Layer 2: Day Trading (M15/M30)
        self.day_strategies = [TrendStrategy(), BreakoutStrategy()]
        # Layer 3: Swing Trading (H4)
        self.swing_strategies = [TrendStrategy(), MeanReversionStrategy()]
        # Layer 4: Position Trading (D1)
        self.position_strategies = [TrendStrategy()]
        
        # Performance tracking per layer
        self.performance = {
            'scalp': deque(maxlen=window),
            'day': deque(maxlen=window),
            'swing': deque(maxlen=window),
            'position': deque(maxlen=window)
        }
        self.weights = {
            'scalp': 0.25,
            'day': 0.25,
            'swing': 0.25,
            'position': 0.25
        }

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

    def get_votes(self, df):
        # df contains multiple timeframes stacked (we need to parse)
        # For simplicity, we assume we have a multi-index or separate calls.
        # We'll implement logic assuming df is the M15 data.
        # In a full implementation, you'd pass timeframes separately.
        # Here's the unified logic:
        signals = {}
        # 1. Scalp signal (M1 – use recent volatility)
        scalp_votes = [s.get_signal(df) for s in self.scalp_strategies]
        # 2. Day signal (M15)
        day_votes = [s.get_signal(df) for s in self.day_strategies]
        # 3. Swing signal (H4 – simulated from M15)
        swing_votes = [s.get_signal(df) for s in self.swing_strategies]
        # 4. Position signal (D1 – simulated from M15)
        position_votes = [s.get_signal(df) for s in self.position_strategies]

        # Weighted aggregation
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
