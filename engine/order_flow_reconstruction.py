import numpy as np
from collections import deque
from utils.logger import setup_logger
logger = setup_logger(__name__)

class OrderFlowReconstructor:
    def __init__(self, window=20):
        self.tick_history = deque(maxlen=window)
        self.latent_liquidity = {'bid': 0, 'ask': 0}

    def add_tick(self, bid, ask, volume=1):
        """Add a new tick to the history."""
        spread = ask - bid
        mid = (bid + ask) / 2
        self.tick_history.append({
            'bid': bid, 'ask': ask, 'mid': mid, 'spread': spread, 'volume': volume
        })

    def reconstruct_depth(self, levels=5):
        """
        Use Bayesian inference to estimate hidden order book depth.
        Returns estimated bid/ask volumes for the next 5 levels.
        """
        if len(self.tick_history) < 5:
            return {'bid_levels': [], 'ask_levels': []}

        # Compute average spread and volatility
        spreads = [t['spread'] for t in self.tick_history]
        avg_spread = np.mean(spreads)
        vol = np.std([t['mid'] for t in self.tick_history])

        # Estimate depth: Higher volatility -> lower depth (thin books)
        depth_factor = max(0.1, 1.0 - (vol / avg_spread))

        # Build synthetic ladder
        current_bid = self.tick_history[-1]['bid']
        current_ask = self.tick_history[-1]['ask']
        step = avg_spread / levels

        bid_levels = []
        ask_levels = []
        for i in range(1, levels+1):
            # Depth falls off exponentially
            vol_est = depth_factor * 100 * np.exp(-i * 0.5)
            bid_levels.append({'price': current_bid - i * step, 'volume': vol_est})
            ask_levels.append({'price': current_ask + i * step, 'volume': vol_est})

        return {'bid_levels': bid_levels, 'ask_levels': ask_levels}

    def get_liquidity_imbalance(self):
        """Compute imbalance from the reconstructed depth."""
        depth = self.reconstruct_depth()
        bid_vol = sum([l['volume'] for l in depth['bid_levels']])
        ask_vol = sum([l['volume'] for l in depth['ask_levels']])
        return (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-6)
