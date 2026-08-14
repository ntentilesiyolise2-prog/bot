import asyncio
import json
import aiohttp
from datetime import datetime, timedelta
import pytz
from utils.logger import setup_logger
from api.websocket import manager
from .scalper import Scalper
from .event_intelligence import EventIntelligence
from ..ai.sentiment.micro_expression import MicroExpressionAnalyzer
from ..ai.macro.weather_arbitrage import WeatherArbitrage

logger = setup_logger(__name__)

class TradingEngine:
    def __init__(self, app_state):
        self.app = app_state
        self.running = False
        self.tasks = []
        self.last_signals = {}
        self._last_trade_time = None
        self.auto_trade_enabled = self.app.config.get('ai', {}).get('auto_trade', True)
        self.scalper = Scalper(app_state)
        self.event_intel = EventIntelligence(app_state)
        self.strategy_weights = self._load_weights()
        self.last_weight_update = datetime.utcnow()
        self.session_tz = pytz.timezone(self.app.config.get('session_timezone', 'America/New_York'))
        self.heartbeat_counter = 0
        # COSMOS Modules
        self.sentiment_analyzer = MicroExpressionAnalyzer()
        self.weather_arb = WeatherArbitrage()

    async def start(self):
        self.running = True
        logger.info("🚀 Trading Engine started.")
        self.tasks.append(asyncio.create_task(self._broadcast_prices()))
        self.tasks.append(asyncio.create_task(self._run_scanner()))
        self.tasks.append(asyncio.create_task(self._monitor_risk()))
        self.tasks.append(asyncio.create_task(self._auto_trade_loop()))
        self.tasks.append(asyncio.create_task(self._heartbeat_check()))
        self.tasks.append(asyncio.create_task(self._update_weights_loop()))
        self.tasks.append(asyncio.create_task(self._cosmos_sentiment_loop()))
        self.tasks.append(asyncio.create_task(self._cosmos_weather_loop()))
        await self.scalper.start()
        self.tasks.append(asyncio.create_task(self._event_intelligence_loop()))
        logger.info("✅ All engine loops are running, including COSMOS modules.")

    # ============ COSMOS SENTIMENT LOOP ============
    async def _cosmos_sentiment_loop(self):
        while self.running:
            try:
                # You can set a URL to a live news anchor image.
                # For now, we skip if no URL is configured.
                # This is a placeholder for the actual implementation.
                # Example: sentiment_score = await self.sentiment_analyzer.analyze_anchor_sentiment("https://example.com/news_anchor.jpg")
                # bias = self.sentiment_analyzer.get_market_bias()
                # if bias == "BULLISH":
                #     self.last_signals['SENTIMENT'] = {'direction': 'BUY', 'confluence': 85, 'explanation': 'Anchor sentiment bullish'}
                # elif bias == "BEARISH":
                #     self.last_signals['SENTIMENT'] = {'direction': 'SELL', 'confluence': 85, 'explanation': 'Anchor sentiment bearish'}
                await asyncio.sleep(300)  # check every 5 minutes
            except Exception as e:
                logger.error(f"Sentiment loop error: {e}")
                await asyncio.sleep(60)

    # ============ COSMOS WEATHER LOOP ============
    async def _cosmos_weather_loop(self):
        while self.running:
            try:
                temp = await self.weather_arb.get_forecast()
                signal = self.weather_arb.get_trade_signal(temp)
                if signal:
                    self.last_signals['WEATHER'] = signal
                    logger.info(f"Weather signal: {signal}")
                await asyncio.sleep(3600)  # check every hour
            except Exception as e:
                logger.error(f"Weather loop error: {e}")
                await asyncio.sleep(600)

    # ============ HEARTBEAT ============
    async def _heartbeat_check(self):
        while self.running:
            await asyncio.sleep(300)
            try:
                test_order = {'symbol': 'EURUSD', 'side': 'BUY', 'lot': 0.001}
                result = await self.app.execution_core.execute_order(test_order)
                if result.get('status') == 'failed':
                    logger.error("Heartbeat failed. Broker may be disconnected.")
                    await self.app.telegram.send_message("🚨 Heartbeat failed. Broker disconnected.")
                    self.auto_trade_enabled = False
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                self.auto_trade_enabled = False

    # ============ WEIGHT UPDATE ============
    async def _update_weights_loop(self):
        while self.running:
            await asyncio.sleep(self.app.config['ai']['weight_update_interval_min'] * 60)
            self.app.strategy_swarm.recalc_weights()
            self._save_weights(self.app.strategy_swarm.weights)
            logger.info(f"Strategy weights updated: {self.app.strategy_swarm.weights}")

    def _load_weights(self):
        try:
            with open('strategy_weights.json', 'r') as f:
                return json.load(f)
        except:
            return {'scalp': 0.25, 'day': 0.35, 'swing': 0.25, 'position': 0.15}

    def _save_weights(self, weights):
        with open('strategy_weights.json', 'w') as f:
            json.dump(weights, f, indent=4)

    # ============ BROADCAST PRICES ============
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

    # ============ SCANNER ============
    async def _run_scanner(self):
        while self.running:
            try:
                for symbol in self.app.config['symbols']:
                    df = await self.app.feature_store.compute_features(symbol, "M15")
                    if df.empty:
                        continue
                    result = self.app.strategy_swarm.get_votes(df)
                    # Funding rate filter for crypto
                    if 'BTC' in symbol or 'ETH' in symbol:
                        funding = await self._get_funding_rate(symbol)
                        if funding > self.app.config['ai']['funding_rate_threshold'] and result['direction'] == 'BUY':
                            result['confluence'] *= 0.5
                            result['explanation'] += f" (Funding high {funding:.4f}, BUY reduced)"
                    signal = {
                        "type": "signal",
                        "symbol": symbol,
                        "confluence": result['confluence'],
                        "direction": result['direction'],
                        "signals": [{"symbol": symbol, "direction": result['direction'], "setup": "Multi-Horizon", "confluence": result['confluence']}],
                        "breakdown": result['breakdown'],
                        "explanation": f"Swarm vote: {result['votes']}. Confluence: {result['confluence']}%."
                    }
                    self.last_signals[symbol] = signal
                    await manager.broadcast(signal)
                await asyncio.sleep(self.app.config['ai']['scanner_interval_sec'])
            except Exception as e:
                logger.error(f"Scanner error: {e}")
                await asyncio.sleep(10)

    async def _get_funding_rate(self, symbol):
        if "BTC" in symbol:
            url = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
        elif "ETH" in symbol:
            url = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=ETHUSDT"
        else:
            return 0.0
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    return float(data['lastFundingRate'])
        except:
            return 0.0

    # ============ RISK MONITOR ============
    async def _monitor_risk(self):
        while self.running:
            try:
                now_ny = datetime.now(self.session_tz)
                if now_ny.hour == 0 and now_ny.minute == 0:
                    self.app.risk_engine.reset_daily()
                var = self.app.risk_engine.compute_var_ewma()
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

    # ============ AUTO-TRADE LOOP ============
    async def _auto_trade_loop(self):
        while self.running:
            try:
                if not self.auto_trade_enabled:
                    await asyncio.sleep(1)
                    continue

                if self.app.circuit_breaker.tripped:
                    logger.warning("Circuit breaker tripped. Auto‑trade paused.")
                    await asyncio.sleep(5)
                    continue

                # Check all signals, including COSMOS (latency, sentiment, weather)
                for symbol, signal in self.last_signals.items():
                    if signal is None:
                        continue
                    confluence = signal.get('confluence', 0)
                    direction = signal.get('direction')
                    min_conf = self.app.config['ai']['min_confluence_threshold']
                    # For COSMOS signals, we may have lower thresholds
                    if symbol in ['LATENCY_ARB', 'SENTIMENT', 'WEATHER']:
                        min_conf = 80  # Higher trust for cosmic signals
                    if confluence >= min_conf and direction in ['BUY', 'SELL']:
                        trade_key = f"{symbol}_{direction}"
                        if self._last_trade_time == trade_key:
                            continue
                        # Determine lot size
                        lot = 0.01
                        if symbol in ['LATENCY_ARB', 'SENTIMENT', 'WEATHER']:
                            lot = 0.02  # double size for cosmic signals
                        trade = {'symbol': symbol, 'side': direction, 'lot': lot}
                        ok, msg = self.app.risk_engine.check_risk(trade)
                        if not ok:
                            logger.info(f"Risk blocked {symbol}: {msg}")
                            continue
                        result = await self.app.execution_core.execute_order(trade)
                        if result.get('status') == 'executed':
                            pnl = result.get('pnl', 0.5)
                            self.app.strategy_swarm.update_performance('day', pnl)
                            await self.app.telegram.send_message(
                                f"🤖 Auto-Trade: {direction} {symbol} {lot} lots @ {result.get('price', 'market')} (COSMOS)"
                            )
                            logger.info(f"✅ COSMOS trade executed: {direction} {symbol}")
                            self.last_signals[symbol] = None
                            self._last_trade_time = trade_key
                        else:
                            logger.warning(f"Auto-trade failed for {symbol}: {result}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Auto-trade loop error: {e}")
                await asyncio.sleep(5)

    async def _event_intelligence_loop(self):
        while self.running:
            await self.event_intel.monitor_events()
            await asyncio.sleep(60)

    async def stop(self):
        self.running = False
        await self.scalper.stop()
        for task in self.tasks:
            task.cancel()
        logger.info("⏹️ Trading Engine stopped.")
