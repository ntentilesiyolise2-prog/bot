import yfinance as yf
from utils.logger import setup_logger

logger = setup_logger(__name__)

class RegimeDetector:
    def __init__(self):
        self.vix_spot = None
        self.vix_future = None
        self.adx = None

    async def update(self, data_fabric):
        # VIX term
        term = await data_fabric.get_vix_term()
        # ADX from feature store (if available)
        # For now, use placeholder
        adx = 25  # dummy
        if term > 1.0 and adx > 25:
            self.regime = "BULLISH"
        elif term < -1.0 and adx > 25:
            self.regime = "BEARISH"
        else:
            self.regime = "CHOPPY"
        return self.regime
