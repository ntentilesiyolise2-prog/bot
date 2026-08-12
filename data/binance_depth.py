import websockets
import json
import asyncio
from utils.logger import setup_logger

logger = setup_logger(__name__)

class BinanceDepth:
    def __init__(self, symbol='btcusdt'):
        self.symbol = symbol.lower()
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@depth20@100ms"
        self.bid_vol = 0
        self.ask_vol = 0
        self.imbalance = 0
        self.last_update = None

    async def start(self):
        async with websockets.connect(self.ws_url) as ws:
            while True:
                try:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    bids = data.get('b', [])
                    asks = data.get('a', [])
                    self.bid_vol = sum(float(b[1]) for b in bids[:10])
                    self.ask_vol = sum(float(a[1]) for a in asks[:10])
                    self.imbalance = (self.bid_vol - self.ask_vol) / (self.bid_vol + self.ask_vol + 1e-6)
                    self.last_update = pd.Timestamp.now()
                    logger.debug(f"Imbalance: {self.imbalance:.4f}")
                except Exception as e:
                    logger.error(f"Depth error: {e}")
                    await asyncio.sleep(1)
