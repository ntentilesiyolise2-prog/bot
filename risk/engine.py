import numpy as np

class RiskEngine:
    def __init__(self, config):
        self.config = config
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.open_positions = []

    def check_risk(self, trade) -> tuple:
        if self.daily_loss >= self.config['risk']['max_daily_loss']:
            return False, "Daily loss limit reached"
        if self.consecutive_losses >= self.config['risk']['max_consecutive_losses']:
            return False, "Max consecutive losses exceeded"
        if len(self.open_positions) >= self.config['risk']['max_open_positions']:
            return False, "Max open positions"
        return True, "OK"

    def update_loss(self, loss: float):
        self.daily_loss += abs(loss)
        if loss > 0:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

    def add_position(self, pos):
        self.open_positions.append(pos)

    def remove_position(self, pos):
        self.open_positions.remove(pos)
