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
        self.broker = None  # active broker
        self.idempotency_cache = set()
        self.journal = TradeJournal()
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return

        # Determine primary broker
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

        # Try connecting to primary broker
        try:
            await self.primary_broker.connect()
            self.broker = self.primary_broker
            logger.info(f"Connected to primary broker: {self.config['execution']['broker']}")
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

    # ========== SMART ORDER ROUTING ==========
    async def execute_order(self, order):
        """
        Place an order with smart routing:
        - Try primary broker.
        - If it fails, fall back to simulator.
        """
        order_id = str(uuid.uuid4())
        if order_id in self.idempotency_cache:
            return {"status": "duplicate", "order_id": order_id}
        self.idempotency_cache.add(order_id)

        # Ensure we have an active broker
        if self.broker is None:
            await self.initialize()

        # Try primary broker
        try:
            result = await self._execute_with_retry(self.broker, order)
            if result.get('status') == 'executed':
                # Save to journal
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
                logger.info(f"✅ Order executed: {order['symbol']} {order['side']}")
                return result
            else:
                logger.warning(f"Primary broker failed: {result}. Falling back to simulator.")
        except Exception as e:
            logger.error(f"Primary broker error: {e}. Falling back to simulator.")

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
                logger.info(f"✅ Simulated order executed: {order['symbol']} {order['side']}")
                return result
            else:
                return {"status": "failed", "error": "All brokers failed"}
        except Exception as e:
            logger.error(f"Fallback simulator error: {e}")
            return {"status": "failed", "error": str(e)}

    async def _execute_with_retry(self, broker, order, max_retries=3):
        for attempt in range(max_retries):
            try:
                result = await broker.place_order(order)
                if result.get('status') in ['executed', 'rejected']:
                    return result
                # If not executed, wait and retry
                await asyncio.sleep(2 ** attempt)  # exponential backoff
            except Exception as e:
                logger.warning(f"Order attempt {attempt+1} failed: {e}")
                await asyncio.sleep(2 ** attempt)
        return {"status": "failed", "error": "Max retries exceeded"}

    # ========== POSITION MANAGEMENT ==========
    async def update_sl_tp(self, symbol, sl=None, tp=None):
        """Update stop loss and take profit for an open position."""
        if self.broker:
            return await self.broker.update_sl_tp(symbol, sl, tp)
        return {"status": "failed", "error": "No active broker"}

    async def flatten_all(self):
        """Close all open positions (panic)."""
        if self.broker:
            return await self.broker.flatten_all()
        return {"status": "failed", "error": "No active broker"}

    # ========== GETTERS ==========
    def get_positions(self):
        if self.broker and hasattr(self.broker, 'positions'):
            return self.broker.positions
        return []
