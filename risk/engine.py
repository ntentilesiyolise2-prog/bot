import numpy as np
import pandas as pd
from scipy.stats import norm
from utils.logger import setup_logger

logger = setup_logger(__name__)

class RiskEngine:
    def __init__(self, config):
        self.config = config
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.open_positions = []
        self.returns_history = []
        self.max_drawdown = 0.0
        self.peak_equity = 0.0
        self.var_lambda = 0.94  # EWMA decay factor

    # ========== VOLATILITY‑ADJUSTED LOSS ==========
    def _get_volatility_adjusted_max_loss(self):
        base_loss = self.config['risk']['max_daily_loss']
        atr = self._get_current_atr()
        avg_atr = self._get_avg_atr() or atr
        ratio = atr / avg_atr if avg_atr > 0 else 1.0
        adjusted = base_loss / max(1.0, ratio)
        return max(adjusted, 5.0)

    def _get_current_atr(self):
        return 20.0  # Placeholder – should be fetched from feature store

    def _get_avg_atr(self):
        return 20.0

    # ========== EWMA VaR ==========
    def compute_var_ewma(self, confidence=0.99, horizon=1):
        if len(self.returns_history) < 10:
            return 20.0
        returns = np.array(self.returns_history[-100:])
        # EWMA variance
        var = np.var(returns)
        for i in range(1, len(returns)):
            var = self.var_lambda * var + (1 - self.var_lambda) * (returns[i] ** 2)
        vol = np.sqrt(var)
        z_score = norm.ppf(confidence)
        var_estimate = z_score * vol * 10000 * np.sqrt(horizon)
        return abs(var_estimate)

    # ========== CHECK RISK ==========
    def check_risk(self, trade):
        max_loss = self._get_volatility_adjusted_max_loss()
        if self.daily_loss >= max_loss:
            return False, f"Daily loss limit (${max_loss:.2f}) exceeded"
        if self.consecutive_losses >= self.config['risk']['max_consecutive_losses']:
            return False, f"Consecutive losses ({self.consecutive_losses}) exceeded"
        if len(self.open_positions) >= self.config['risk']['max_open_positions']:
            return False, "Max open positions"
        var = self.compute_var_ewma()
        if var > max_loss * 0.8:
            return False, f"VaR too high (${var:.2f})"
        return True, "OK"

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

    def reset_daily(self):
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        logger.info("Daily risk counters reset.")

    def add_position(self, pos):
        self.open_positions.append(pos)

    def remove_position(self, pos):
        if pos in self.open_positions:
            self.open_positions.remove(pos)
