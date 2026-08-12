import uuid
import asyncio
from .simulator import Simulator
from .mt5_broker import MT5Broker
from .alpaca_broker import AlpacaBroker
from utils.journal import TradeJournal
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ExecutionCore:
    def __init__(self, config):
        self.config = config
        self.broker = None
        self.simulator = Simulator()
        self.idempotency_cache = set()
        self.journal = TradeJournal()  # <-- Journal integrated

    async def initialize(self):
        if self.config['execution']['paper_trading']:
            self.broker = self.simulator
        else:
            broker_type = self.config['execution']['broker']
            if broker_type == 'mt5':
                self.broker = MT5Broker(self.config['execution']['mt5_account'])
            elif broker_type == 'alpaca':
                self.broker = AlpacaBroker(self.config['execution']['alpaca_account'])
            else:
                raise ValueError(f"Unsupported broker: {broker_type}")
            await self.broker.connect()
        await self.broker.connect()
        logger.info("ExecutionCore initialized.")

    async def shutdown(self):
        await self.broker.disconnect()
        logger.info("ExecutionCore shutdown.")

    async def execute_order(self, order):
        order_id = str(uuid.uuid4())
        if order_id in self.idempotency_cache:
            return {"status": "duplicate", "order_id": order_id}
        self.idempotency_cache.add(order_id)

        try:
            result = await self.broker.place_order(order)
            if result.get('status') == 'executed':
                # Save to journal (only if it's a real trade, not a test)
                self.journal.add_trade({
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'entry': result.get('price', 0),
                    'exit': result.get('price', 0),  # Will be updated on close
                    'pnl': 0,  # Will be updated on close
                    'source': 'bot',
                    'order_id': result.get('id')
                })
                logger.info(f"Order executed: {order['symbol']} {order['side']}")
            return result
        except Exception as e:
            # Retry logic
            for attempt in range(3):
                await asyncio.sleep(1)
                try:
                    result = await self.broker.place_order(order)
                    if result.get('status') == 'executed':
                        self.journal.add_trade({
                            'symbol': order['symbol'],
                            'side': order['side'],
                            'entry': result.get('price', 0),
                            'exit': result.get('price', 0),
                            'pnl': 0,
                            'source': 'bot',
                            'order_id': result.get('id')
                        })
                        return result
                except:
                    continue
            return {"status": "failed", "error": str(e)}

    async def close_position(self, position):
        # Simulate closing a position (called by the risk engine or auto-trade loop)
        # In a real broker, you would send a close order.
        # For the simulator, we update PnL and save to journal.
        if hasattr(self.broker, 'close_position'):
            result = await self.broker.close_position(position)
        else:
            # Simulator close: just calculate PnL
            entry = position['entry_price']
            current = position['current_price']
            lot = position['lot']
            side = position['side']
            if side == 'BUY':
                pnl = (current - entry) * lot * 100
            else:
                pnl = (entry - current) * lot * 100
            result = {"status": "closed", "pnl": pnl}
        
        # Update journal with final PnL
        if result.get('status') == 'closed':
            # Find the trade in the journal by order_id or symbol/time
            # For simplicity, we add a new entry with the final PnL
            self.journal.add_trade({
                'symbol': position['symbol'],
                'side': position['side'],
                'entry': position['entry_price'],
                'exit': position.get('exit_price', position['current_price']),
                'pnl': result.get('pnl', 0),
                'source': 'bot',
                'closed_at': datetime.utcnow().isoformat()
            })
            logger.info(f"Position closed: {position['symbol']} PnL: {result.get('pnl', 0)}")
        return result
