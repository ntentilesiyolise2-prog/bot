import numpy as np
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DigitalTwin:
    def __init__(self, historical_data):
        self.data = historical_data
        self.cache = {}

    def simulate_trade(self, trade, n_scenarios=100):
        results = []
        for _ in range(n_scenarios):
            path = self.generate_path()
            pnl = self.evaluate_trade(trade, path)
            results.append(pnl)
        if not results:
            return {'expected_pnl': 0, 'confidence': 0, 'win_prob': 0}
        return {
            'expected_pnl': np.mean(results),
            'confidence': 1 - (np.std(results) / (np.mean(results) + 1e-6)) if np.mean(results) > 0 else 0,
            'win_prob': np.mean([1 if p > 0 else 0 for p in results])
        }

    def generate_path(self, length=5):
        if self.data.empty:
            return [100] * length
        last_price = self.data['Close'].iloc[-1]
        vol = self.data['Close'].pct_change().std()
        drift = np.mean(self.data['Close'].pct_change())
        path = [last_price]
        for _ in range(length):
            path.append(path[-1] * (1 + drift + np.random.normal(0, vol)))
        return path

    def evaluate_trade(self, trade, path):
        entry = path[0]
        exit_price = path[-1]
        if trade['side'] == 'BUY':
            return (exit_price - entry) * float(trade.get('lot', 0.01)) * 100
        else:
            return (entry - exit_price) * float(trade.get('lot', 0.01)) * 100
