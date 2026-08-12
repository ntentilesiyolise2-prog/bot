import asyncio
import websockets
import json
from utils.logger import setup_logger
from execution.core import ExecutionCore

logger = setup_logger(__name__)

class Scalper:
    def __init__(self, app_state):
        self.app = app_state
        self.symbols = ['BTCUSDT', 'ETHUSDT']
        self.depth_cache = {}
        self.trade_cache = {}
        self.running = False

    async def start(self):
        self.running = True
        asyncio.create_task(self._scalp_loop())

    async def _scalp_loop(self):
        while self.running:
            for symbol in self.symbols:
                await self._process_scalp(symbol)
            await asyncio.sleep(1)  # Check every second

    async def _process_scalp(self, symbol):
        # Get depth (order book) from cache
        depth = self.depth_cache.get(symbol)
        if not depth:
            return
        # Calculate imbalance
        bids = depth.get('b', [])
        asks = depth.get('a', [])
        bid_vol = sum(float(b[1]) for b in bids[:10])
        ask_vol = sum(float(a[1]) for a in asks[:10])
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-6)

        # Get last trades for VWAP
        trades = self.trade_cache.get(symbol, [])
        if not trades:
            return
        vwap = sum(t['p'] * t['q'] for t in trades[-50:]) / sum(t['q'] for t in trades[-50:]) if trades else None
        if vwap is None:
            return

        # Entry logic: sweep VWAP if imbalance is strong
        current_price = float(depth['b'][0][0])  # best bid as proxy
        entry = vwap
        if imbalance > 0.6:  # strong buying pressure
            # Go long if price is near VWAP
            if abs(current_price - vwap) / vwap < 0.001:
                logger.info(f"Scalp BUY {symbol} @ {current_price}")
                await self.app.execution_core.execute_order({'symbol': symbol, 'side': 'BUY', 'lot': 0.01})
        elif imbalance < -0.6:
            if abs(current_price - vwap) / vwap < 0.001:
                logger.info(f"Scalp SELL {symbol} @ {current_price}")
                await self.app.execution_core.execute_order({'symbol': symbol, 'side': 'SELL', 'lot': 0.01})
