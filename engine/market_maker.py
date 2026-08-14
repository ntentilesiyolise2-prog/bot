import asyncio
import random
from utils.logger import setup_logger
logger = setup_logger(__name__)

class MarketMaker:
    def __init__(self, app_state):
        self.app = app_state
        self.running = False
        self.symbols = ['EURUSD', 'BTCUSD']

    async def start(self):
        self.running = True
        asyncio.create_task(self._market_make_loop())

    async def _market_make_loop(self):
        while self.running:
            for symbol in self.symbols:
                df = await self.app.data_fabric.get_candles(symbol, "M1", limit=1)
                if df.empty:
                    continue
                price = df['Close'].iloc[-1]
                spread = random.uniform(0.0001, 0.0005)
                buy_price = price - spread / 2
                sell_price = price + spread / 2
                logger.info(f"Market Making: {symbol} BUY LIMIT @ {buy_price:.5f}, SELL LIMIT @ {sell_price:.5f}")
                # In live, you'd place actual LIMIT orders here.
            await asyncio.sleep(5)

    async def stop(self):
        self.running = False
