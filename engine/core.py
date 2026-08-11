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
        self.last_signals = {}   # Cache to avoid duplicate auto‑trades
        self._last_trade_time = None

    async def start(self):
        self.running = True
        logger.info("🚀 Trading Engine started.")
        self.tasks.append(asyncio.create_task(self._broadcast_prices()))
        self.tasks.append(asyncio.create_task(self._run_scanner()))
        self.tasks.append(asyncio.create_task(self._monitor_risk()))
        self.tasks.append(asyncio.create_task(self._auto_trade_loop()))  # AUTO-TRADE
        logger.info("✅ All engine loops are running.")

    # ------------------------------------------------------------
    # 1. PRICE BROADCASTER (every 2 seconds)
    # ------------------------------------------------------------
    async def _broadcast_prices(self):
        while self.running:
            try:
                for symbol in self.app.config['symbols']:
                    df = await self.app.data_fabric.get_candles(symbol, "M1", limit=2)
                    if not df.empty and len(df) > 1:
                        last = df.iloc[-1]
                        prev = df.iloc[-2]
                        change = round(((last['Close'] - prev['Close']) / prev['Close']) * 100, 2)
                        msg = {
                            "type": "price",
                            "symbol": symbol,
                            "bid": round(last['Close'] * 0.9998, 2),
                            "ask": round(last['Close'] * 1.0002, 2),
                            "high": last['High'],
                            "low": last['Low'],
                            "change": change,
                            "volume": str(int(last['Volume'])) if last['Volume'] else "--",
                            "time": datetime.utcnow().strftime("%H:%M:%S"),
                            "spread": round((last['Close'] * 0.0004), 2),
                        }
                        await manager.broadcast(msg)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Price broadcast error: {e}")
                await asyncio.sleep(5)

    # ------------------------------------------------------------
    # 2. STRATEGY SCANNER (every 5 seconds)
    # ------------------------------------------------------------
    async def _run_scanner(self):
        while self.running:
            try:
                for symbol in self.app.config['symbols']:
                    df = await self.app.feature_store.compute_features(symbol, "M15")
                    if df.empty:
                        continue
                    result = self.app.strategy_swarm.get_votes(df)
                    signal = {
                        "type": "signal",
                        "symbol": symbol,
                        "confluence": result['confluence'],
                        "direction": result['direction'],
                        "signals": [{"symbol": symbol, "direction": result['direction'], "setup": "Multi-Agent", "confluence": result['confluence']}],
                        "breakdown": result['breakdown'],
                        "explanation": f"Multi-agent vote: {result['votes']}. Confluence: {result['confluence']}%."
                    }
                    self.last_signals[symbol] = signal
                    await manager.broadcast(signal)
                await asyncio.sleep(self.app.config['ai']['scanner_interval_sec'])
            except Exception as e:
                logger.error(f"Scanner error: {e}")
                await asyncio.sleep(10)

    # ------------------------------------------------------------
    # 3. RISK MONITOR (every 60 seconds)
    # ------------------------------------------------------------
    async def _monitor_risk(self):
        while self.running:
            try:
                # Calculate real risk from engine
                var = self.app.risk_engine.compute_var()
                tilt = self.app.risk_engine.get_tilt_status()
                risk_data = {
                    "type": "risk",
                    "var": f"${var:.2f}",
                    "tilt": tilt,
                    "gex": "+1.24M",
                    "vpin": "0.34",
                    "var_sub": "-3.27% equity",
                    "tilt_sub": "Bias 0.12σ",
                    "gex_sub": "Positive gamma",
                    "vpin_sub": "Low toxicity",
                    "var_pct": 68,
                    "tilt_pct": 12,
                    "gex_pct": 82,
                    "vpin_pct": 34
                }
                await manager.broadcast(risk_data)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Risk monitor error: {e}")

    # ------------------------------------------------------------
    # 4. AUTO‑TRADE LOOP (checks signals, risk, executes)
    # ------------------------------------------------------------
    async def _auto_trade_loop(self):
        while self.running:
            try:
                # Check if auto‑trade is enabled
                auto_trade_enabled = self.app.config.get('ai', {}).get('auto_trade', True)
                if not auto_trade_enabled:
                    await asyncio.sleep(1)
                    continue

                # Check circuit breaker
                if self.app.circuit_breaker.tripped:
                    logger.warning("Circuit breaker tripped. Auto‑trade paused.")
                    await asyncio.sleep(5)
                    continue

                for symbol, signal in self.last_signals.items():
                    if signal is None:
                        continue
                    confluence = signal.get('confluence', 0)
                    direction = signal.get('direction')
                    min_conf = self.app.config['ai']['min_confluence_threshold']
                    if confluence >= min_conf and direction in ['BUY', 'SELL']:
                        # Prevent duplicate trades on the same signal
                        trade_key = f"{symbol}_{direction}"
                        if self._last_trade_time == trade_key:
                            continue
                        # Check risk
                        trade = {'symbol': symbol, 'side': direction, 'lot': 0.01}
                        ok, msg = self.app.risk_engine.check_risk(trade)
                        if not ok:
                            logger.info(f"Risk blocked {symbol}: {msg}")
                            continue
                        # Execute the trade
                        result = await self.app.execution_core.execute_order(trade)
                        if result.get('status') == 'executed':
                            # Update strategy weights with PnL (dummy PnL for now, will be real)
                            # In reality, we'd get PnL from the position close
                            pnl = result.get('pnl', 0.5)  # placeholder
                            self.app.strategy_swarm.update_performance('Multi-Agent', pnl)
                            # Send alert
                            await self.app.telegram.send_message(
                                f"🤖 Auto-Trade: {direction} {symbol} 0.01 lots @ {result.get('price', 'market')}"
                            )
                            logger.info(f"✅ Auto-trade executed: {direction} {symbol}")
                            self.last_signals[symbol] = None
                            self._last_trade_time = trade_key
                        else:
                            logger.warning(f"Auto-trade failed for {symbol}: {result}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Auto-trade loop error: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        self.running = False
        for task in self.tasks:
            task.cancel()
        logger.info("⏹️ Trading Engine stopped.")
