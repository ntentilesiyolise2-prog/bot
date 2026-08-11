import numpy as np
from scipy.stats import norm

class RiskEngine:
    def __init__(self, config):
        self.config = config
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.open_positions = []
        self.returns_history = []

    def check_risk(self, trade):
        if self.daily_loss >= self.config['risk']['max_daily_loss']:
            return False, "Daily loss limit reached"
        if self.consecutive_losses >= self.config['risk']['max_consecutive_losses']:
            return False, "Max consecutive losses exceeded"
        if len(self.open_positions) >= self.config['risk']['max_open_positions']:
            return False, "Max open positions"
        if self.compute_var() > self.config['risk']['max_daily_loss'] * 0.8:
            return False, "VaR too high"
        return True, "OK"

    def compute_var(self, confidence=0.99, horizon=1):
        if len(self.returns_history) < 20:
            return 20.0  # Default VaR
        returns = np.array(self.returns_history[-100:])
        var = np.percentile(returns, (1 - confidence) * 100) * 10000
        return abs(var)

    def get_tilt_status(self):
        if self.consecutive_losses >= 3:
            return "OVERTRADING"
        elif len(self.open_positions) >= self.config['risk']['max_open_positions'] - 1:
            return "OVERLEVERAGED"
        return "NEUTRAL"

    def update_loss(self, loss):
        self.daily_loss += abs(loss)
        self.returns_history.append(loss)
        if loss > 0:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

    def add_position(self, pos):
        self.open_positions.append(pos)

    def remove_position(self, pos):
        self.open_positions.remove(pos)
