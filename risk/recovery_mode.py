from utils.logger import setup_logger

logger = setup_logger(__name__)

class RecoveryMode:
    def __init__(self, circuit_breaker):
        self.cb = circuit_breaker
        self.recovery_active = False
        self.recovery_step = 0

    def check(self):
        if self.cb.tripped:
            self.recovery_active = True
            logger.warning("Recovery mode activated.")
            # Reduce risk further
            self.cb.max_daily_loss /= 2
            self.cb.consecutive_loss_limit = 1
            return True
        return False

    def progress(self):
        if self.recovery_active:
            self.recovery_step += 1
            if self.recovery_step >= 10:
                # Gradually restore
                self.cb.max_daily_loss *= 1.2
                self.cb.consecutive_loss_limit = 2
                if self.cb.max_daily_loss > self.cb.original_max_daily_loss * 0.8:
                    self.recovery_active = False
                    self.recovery_step = 0
                    logger.info("Recovery complete.")
            return self.recovery_active
        return False
