import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from utils.logger import setup_logger

logger = setup_logger(__name__)

class AlpacaBroker:
    def __init__(self, account_config):
        self.api_key = account_config.get('api_key', os.getenv("ALPACA_API_KEY"))
        self.secret_key = account_config.get('secret_key', os.getenv("ALPACA_SECRET_KEY"))
        self.paper = account_config.get('paper', True)
        self.client = None
        self.connected = False

    async def connect(self):
        try:
            self.client = TradingClient(self.api_key, self.secret_key, paper=self.paper)
            self.connected = True
            logger.info("Alpaca connected")
            return True
        except Exception as e:
            logger.error(f"Alpaca connect error: {e}")
            return False

    async def disconnect(self):
        self.connected = False
        logger.info("Alpaca disconnected")

    async def place_order(self, order):
        if not self.connected:
            return {"status": "failed", "error": "Not connected"}
        try:
            side = OrderSide.BUY if order['side'] == 'BUY' else OrderSide.SELL
            request = MarketOrderRequest(
                symbol=order['symbol'],
                qty=float(order['lot']),
                side=side,
                time_in_force=TimeInForce.DAY
            )
            result = self.client.submit_order(request)
            return {
                "status": "executed",
                "id": result.id,
                "symbol": result.symbol,
                "side": result.side,
                "lot": float(result.qty),
                "price": float(result.filled_avg_price or result.limit_price or 0)
            }
        except Exception as e:
            logger.error(f"Alpaca order error: {e}")
            return {"status": "failed", "error": str(e)}
