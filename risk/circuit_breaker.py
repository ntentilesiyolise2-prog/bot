class CircuitBreaker:
    def __init__(self, max_daily_loss=50, consecutive_loss_limit=3):
        self.max_daily_loss = max_daily_loss
        self.consecutive_loss_limit = consecutive_loss_limit
        self.daily_loss = 0
        self.consecutive_losses = 0
        self.tripped = False

    def update(self, pnl):
        if pnl < 0:
            self.daily_loss += abs(pnl)
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        if self.daily_loss > self.max_daily_loss or self.consecutive_losses >= self.consecutive_loss_limit:
            self.tripped = True

    def reset(self):
        self.daily_loss = 0
        self.consecutive_losses = 0
        self.tripped = False
