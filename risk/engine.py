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

    # ========== BASE CHECKS ==========
    def check_risk(self, trade):
        """Check if a trade is allowed based on current risk parameters."""
        # Volatility-adjusted max daily loss
        max_loss = self._get_volatility_adjusted_max_loss()

        if self.daily_loss >= max_loss:
            return False, f"Daily loss limit reached (${self.daily_loss:.2f} >= ${max_loss:.2f})"

        if self.consecutive_losses >= self.config['risk']['max_consecutive_losses']:
            return False, f"Max consecutive losses ({self.consecutive_losses}) exceeded"

        if len(self.open_positions) >= self.config['risk']['max_open_positions']:
            return False, "Max open positions"

        var = self.compute_var()
        if var > max_loss * 0.8:
            return False, f"VaR too high (${var:.2f} > ${max_loss * 0.8:.2f})"

        return True, "OK"

    # ========== VOLATILITY‑ADJUSTED LOSS LIMIT ==========
    def _get_volatility_adjusted_max_loss(self):
        """Dynamic max daily loss based on current volatility."""
        base_loss = self.config['risk']['max_daily_loss']
        # Get current ATR (if available from open positions or market data)
        atr = self._get_current_atr()
        avg_atr = self._get_avg_atr() or atr
        ratio = atr / avg_atr if avg_atr > 0 else 1.0
        # If volatility doubles, max loss halves
        adjusted = base_loss / max(1.0, ratio)
        # Floor at $5 to prevent absurdly low limits
        return max(adjusted, 5.0)

    def _get_current_atr(self):
        """Get current ATR from open positions or a default."""
        # Simplified – in production, fetch from market data
        return 20.0  # placeholder

    def _get_avg_atr(self):
        """Get average ATR over the last 20 candles."""
        # In production, fetch from feature store
        return 20.0  # placeholder

    # ========== VaR / CVaR ==========
    def compute_var(self, confidence=0.99, horizon=1):
        if len(self.returns_history) < 20:
            return 20.0  # default VaR

        returns = np.array(self.returns_history[-100:])
        # Scale for horizon
        var = np.percentile(returns, (1 - confidence) * 100) * 10000 * np.sqrt(horizon)
        return abs(var)

    def compute_cvar(self, confidence=0.99):
        if len(self.returns_history) < 20:
            return 30.0
        returns = np.array(self.returns_history[-100:])
        var = np.percentile(returns, (1 - confidence) * 100)
        cvar = returns[returns <= var].mean()
        return abs(cvar) * 10000

    # ========== TILT DETECTION ==========
    def get_tilt_status(self):
        if self.consecutive_losses >= 3:
            return "OVERTRADING"
        elif len(self.open_positions) >= self.config['risk']['max_open_positions'] - 1:
            return "OVERLEVERAGED"
        return "NEUTRAL"

    # ========== DRAWDOWN ==========
    def update_drawdown(self, current_equity):
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if self.peak_equity > 0:
            dd = (self.peak_equity - current_equity) / self.peak_equity * 100
            self.max_drawdown = max(self.max_drawdown, dd)
        return self.max_drawdown

    # ========== POSITION MANAGEMENT ==========
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
        if pos in self.open_positions:
            self.open_positions.remove(pos)

    # ========== RESET ==========
    def reset_daily(self):
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        logger.info("Daily risk counters reset.")
