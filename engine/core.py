import asyncio
import json
from datetime import datetime
from utils.logger import setup_logger
from api.websocket import manager
from data.symbol_info import SymbolInfo

logger = setup_logger(__name__)

class TradingEngine:
    def __init__(self, app_state):
        self.app = app_state
        self.running = False
        self.tasks = []
        self.last_signals = {}
        self._last_trade_time = None
        self.active_symbols = set(self.app.config.get('symbols', ['BTCUSD', 'EURUSD']))
        self.symbol_info = SymbolInfo()
        self.symbol_metadata_cache = {}

    async def start(self):
        self.running = True
        logger.info("🚀 Universal Trading Engine started.")
        # If load_all_symbols is true, load a default set (top 10) from the exchange.
        if self.app.config.get('load_all_symbols', False):
            await self._load_default_symbols()
        self.tasks.append(asyncio.create_task(self._broadcast_prices()))
        self.tasks.append(asyncio.create_task(self._run_scanner()))
        self.tasks.append(asyncio.create_task(self._monitor_risk()))
        self.tasks.append(asyncio.create_task(self._auto_trade_loop()))
        logger.info(f"✅ Active symbols: {self.active_symbols}")

    async def add_symbol(self, symbol):
        """Dynamically add a symbol to the watchlist."""
        if symbol in self.active_symbols:
            return False
        # Validate symbol
        meta = self.symbol_info.get_symbol_metadata(symbol)
        if meta:
            self.active_symbols.add(symbol)
            self.symbol_metadata_cache[symbol] = meta
            logger.info(f"➕ Added symbol: {symbol}")
            return True
        logger.warning(f"❌ Symbol not found: {symbol}")
        return False

    async def remove_symbol(self, symbol):
        if symbol in self.active_symbols:
            self.active_symbols.remove(symbol)
            logger.info(f"➖ Removed symbol: {symbol}")
            return True
        return False

    async def _load_default_symbols(self):
        defaults = ['BTCUSD', 'ETHUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'AAPL', 'SPX']
        for sym in defaults:
            await self.add_symbol(sym)

    async def _get_symbol_metadata(self, symbol):
        if symbol not in self.symbol_metadata_cache:
            meta = self.symbol_info.get_symbol_metadata(symbol)
            if meta:
                self.symbol_metadata_cache[symbol] = meta
        return self.symbol_metadata_cache.get(symbol, {})

    async def _broadcast_prices(self):
        while self.running:
            try:
                for symbol in list(self.active_symbols):
                    df = await self.app.data_fabric.get_candles(symbol, "M1", limit=2)
                    if not df.empty and len(df) > 1:
                        last = df.iloc[-1]
                        prev = df.iloc[-2]
                        change = round(((last['Close'] - prev['Close']) / prev['Close']) * 100, 2)
                        meta = await self._get_symbol_metadata(symbol)
                        digits = meta.get('digits', 2)
                        msg = {
                            "type": "price",
                            "symbol": symbol,
                            "bid": round(last['Close'] * 0.9998, digits),
                            "ask": round(last['Close'] * 1.0002, digits),
                            "high": last['High'],
                            "low": last['Low'],
                            "change": change,
                            "volume": str(int(last['Volume'])) if last['Volume'] else "--",
                            "time": datetime.utcnow().strftime("%H:%M:%S"),
                            "spread": round((last['Close'] * 0.0004), digits),
                        }
                        await manager.broadcast(msg)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Price broadcast error: {e}")
                await asyncio.sleep(5)

    async def _run_scanner(self):
        while self.running:
            try:
                for symbol in list(self.active_symbols):
                    df = await self.app.feature_store.compute_features(symbol, "M15")
                    if df.empty:
                        continue
                    # Get symbol metadata for adaptive strategy parameters
                    meta = await self._get_symbol_metadata(symbol)
                    # Run strategy swarm (already adaptive via ATR)
                    result = self.app.strategy_swarm.get_votes(df)
                    signal = {
                        "type": "signal",
                        "symbol": symbol,
                        "confluence": result['confluence'],
                        "direction": result['direction'],
                        "signals": [{"symbol": symbol, "direction": result['direction'], "setup": "Universal", "confluence": result['confluence']}],
                        "breakdown": result['breakdown'],
                        "explanation": f"Swarm vote: {result['votes']}. Confluence: {result['confluence']}%. Digits: {meta.get('digits', 4)}"
                    }
                    self.last_signals[symbol] = signal
                    await manager.broadcast(signal)
                await asyncio.sleep(self.app.config['ai']['scanner_interval_sec'])
            except Exception as e:
                logger.error(f"Scanner error: {e}")
                await asyncio.sleep(10)

    async def _monitor_risk(self):
        while self.running:
            try:
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

    async def _auto_trade_loop(self):
        while self.running:
            try:
                auto_trade_enabled = self.app.config.get('ai', {}).get('auto_trade', True)
                if not auto_trade_enabled:
                    await asyncio.sleep(1)
                    continue

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
                        trade_key = f"{symbol}_{direction}"
                        if self._last_trade_time == trade_key:
                            continue
                        trade = {'symbol': symbol, 'side': direction, 'lot': 0.01}
                        ok, msg = self.app.risk_engine.check_risk(trade)
                        if not ok:
                            logger.info(f"Risk blocked {symbol}: {msg}")
                            continue
                        result = await self.app.execution_core.execute_order(trade)
                        if result.get('status') == 'executed':
                            pnl = result.get('pnl', 0.5)
                            self.app.strategy_swarm.update_performance('Universal', pnl)
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
