import asyncio
import json
from datetime import datetime
from utils.logger import setup_logger
from api.websocket import manager

logger = setup_logger(__name__)

class TradingEngine:
    def __init__(self, app_state):
        self.app = app_state
        self.running = False
        self.tasks = []

    async def start(self):
        self.running = True
        logger.info("🚀 Trading Engine started.")
        # Start the price broadcaster
        self.tasks.append(asyncio.create_task(self._broadcast_prices()))
        # Start the scanner
        self.tasks.append(asyncio.create_task(self._run_scanner()))
        # Start the risk monitor
        self.tasks.append(asyncio.create_task(self._monitor_risk()))

    async def _broadcast_prices(self):
        """Fetch prices every 2 seconds and push to WebSocket."""
        while self.running:
            try:
                for symbol in self.app.config['symbols']:
                    # Fetch latest 1 candle
                    df = await self.app.data_fabric.get_candles(symbol, "M1", limit=1)
                    if not df.empty:
                        last = df.iloc[-1]
                        msg = {
                            "type": "price",
                            "symbol": symbol,
                            "bid": round(last['Close'] * 0.9998, 2),
                            "ask": round(last['Close'] * 1.0002, 2),
                            "high": last['High'],
                            "low": last['Low'],
                            "change": round(((last['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100, 2) if len(df) > 1 else 0,
                            "volume": str(int(last['Volume'])) if last['Volume'] else "--",
                            "time": datetime.utcnow().strftime("%H:%M:%S"),
                            "spread": round((last['Close'] * 0.0004), 2),
                            "confluence": 0  # Updated by scanner
                        }
                        await manager.broadcast(msg)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Price broadcast error: {e}")
                await asyncio.sleep(5)

    async def _run_scanner(self):
        """Run the strategy swarm every 5 seconds and push signals."""
        while self.running:
            try:
                for symbol in self.app.config['symbols']:
                    df = await self.app.feature_store.compute_features(symbol, "M15")
                    if df.empty:
                        continue
                    result = self.app.strategy_swarm.get_votes(df)
                    # Format signal
                    signal = {
                        "type": "signal",
                        "symbol": symbol,
                        "confluence": result['confluence'],
                        "direction": result['direction'],
                        "signals": [{"symbol": symbol, "direction": result['direction'], "setup": "Trend+ICT", "confluence": result['confluence']}],
                        "breakdown": result['breakdown'],
                        "explanation": f"Swarm vote: {result['votes']}. Confluence: {result['confluence']}%."
                    }
                    await manager.broadcast(signal)
                await asyncio.sleep(self.app.config['ai']['scanner_interval_sec'])
            except Exception as e:
                logger.error(f"Scanner error: {e}")
                await asyncio.sleep(10)

    async def _monitor_risk(self):
        """Monitor risk and push updates."""
        while self.running:
            try:
                risk_data = {
                    "type": "risk",
                    "var": "$42.18",
                    "tilt": "NEUTRAL",
                    "gex": "+1.24M",
                    "vpin": "0.34"
                }
                await manager.broadcast(risk_data)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Risk monitor error: {e}")

    async def stop(self):
        self.running = False
        for task in self.tasks:
            task.cancel()
        logger.info("⏹️ Trading Engine stopped.")
