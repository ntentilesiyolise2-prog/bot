import uuid
import asyncio
import concurrent.futures
from datetime import datetime
from .simulator import Simulator
from .mt5_broker import MT5Broker
from .alpaca_broker import AlpacaBroker
from utils.journal import TradeJournal
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ExecutionCore:
    def __init__(self, config):
        self.config = config
        self.primary_broker = None
        self.simulator = Simulator()
        self.broker = None
        self.idempotency_cache = set()
        self.journal = TradeJournal()
        self._initialized = False
        self.correlation_cache = {}

    async def initialize(self):
        if self._initialized:
            return

        if self.config['execution']['paper_trading']:
            self.primary_broker = self.simulator
        else:
            broker_type = self.config['execution']['broker']
            if broker_type == 'mt5':
                self.primary_broker = MT5Broker(self.config['execution']['mt5_account'])
            elif broker_type == 'alpaca':
                self.primary_broker = AlpacaBroker(self.config['execution']['alpaca_account'])
            else:
                raise ValueError(f"Unsupported broker: {broker_type}")

        try:
            await self.primary_broker.connect()
            self.broker = self.primary_broker
            logger.info(f"Connected to primary broker")
        except Exception as e:
            logger.warning(f"Failed to connect to primary broker: {e}. Falling back to simulator.")
            await self.simulator.connect()
            self.broker = self.simulator

        self._initialized = True
        logger.info("ExecutionCore initialized.")

    async def shutdown(self):
        if self.broker:
            await self.broker.disconnect()
        logger.info("ExecutionCore shutdown.")

    # ========== SMART ORDER ROUTING + TIMEOUT + PARTIAL FILL ==========
    async def execute_order(self, order):
        order_id = str(uuid.uuid4())
        if order_id in self.idempotency_cache:
            return {"status": "duplicate", "order_id": order_id}
        self.idempotency_cache.add(order_id)

        if self.broker is None:
            await self.initialize()

        # Correlation risk check
        if self.config['risk']['auto_hedge']:
            corr = await self._get_correlation(order['symbol'])
            if corr > self.config['risk']['correlation_threshold']:
                logger.warning(f"Correlation {corr:.2f} too high for {order['symbol']}. Reducing lot by 50%.")
                order['lot'] *= 0.5

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                self._execute_with_retry(self.broker, order),
                timeout=self.config['execution']['order_timeout_sec']
            )
            if result.get('status') == 'executed':
                self.journal.add_trade({
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'entry': result.get('price', 0),
                    'exit': result.get('price', 0),
                    'pnl': 0,
                    'source': 'bot',
                    'order_id': order_id,
                    'status': 'open'
                })
                # Check for partial fill
                if result.get('filled_lot', 0) < order['lot']:
                    remaining = order['lot'] - result['filled_lot']
                    logger.warning(f"Partial fill. Remaining {remaining} lots. Sending new order.")
                    new_order = order.copy()
                    new_order['lot'] = remaining
                    await self.execute_order(new_order)
                return result
            else:
                logger.warning(f"Order failed. Falling back to simulator.")
        except asyncio.TimeoutError:
            logger.error(f"Order timed out after {self.config['execution']['order_timeout_sec']}s.")
            # Cancel pending order on broker (if possible)
            await self.broker.cancel_order(order_id)
            return {"status": "failed", "error": "Timeout"}

        # Fallback to simulator
        try:
            if self.broker != self.simulator:
                await self.simulator.connect()
                self.broker = self.simulator
            result = await self._execute_with_retry(self.broker, order)
            if result.get('status') == 'executed':
                self.journal.add_trade({
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'entry': result.get('price', 0),
                    'exit': result.get('price', 0),
                    'pnl': 0,
                    'source': 'bot_simulated',
                    'order_id': order_id,
                    'status': 'open'
                })
                return result
        except Exception as e:
            logger.error(f"Fallback simulator error: {e}")
            return {"status": "failed", "error": str(e)}

    async def _execute_with_retry(self, broker, order, max_retries=3):
        for attempt in range(max_retries):
            try:
                result = await broker.place_order(order)
                if result.get('status') in ['executed', 'rejected']:
                    return result
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f"Order attempt {attempt+1} failed: {e}")
                await asyncio.sleep(2 ** attempt)
        return {"status": "failed", "error": "Max retries exceeded"}

    async def _get_correlation(self, symbol):
        # Simplified: fetch recent returns and compute correlation with open positions
        # In full implementation, use the correlation matrix endpoint
        return 0.0  # Placeholder

    async def update_sl_tp(self, symbol, sl=None, tp=None):
        if self.broker:
            return await self.broker.update_sl_tp(symbol, sl, tp)
        return {"status": "failed", "error": "No active broker"}

    async def flatten_all(self):
        if self.broker:
            return await self.broker.flatten_all()
        return {"status": "failed", "error": "No active broker"}

    def get_positions(self):
        if self.broker and hasattr(self.broker, 'positions'):
            return self.broker.positions
        return []
