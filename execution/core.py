import uuid
import asyncio
from .simulator import Simulator
from .mt5_broker import MT5Broker

class ExecutionCore:
    def __init__(self, config):
        self.config = config
        self.broker = None
        self.simulator = Simulator()
        self.idempotency_cache = set()

    async def initialize(self):
        if self.config['execution']['paper_trading']:
            self.broker = self.simulator
        else:
            broker_type = self.config['execution']['broker']
            if broker_type == 'mt5':
                self.broker = MT5Broker(self.config['execution']['mt5_account'])
            else:
                raise ValueError(f"Unsupported broker: {broker_type}")
            await self.broker.connect()
        await self.broker.connect()

    async def shutdown(self):
        await self.broker.disconnect()

    async def execute_order(self, order):
        order_id = str(uuid.uuid4())
        if order_id in self.idempotency_cache:
            return {"status": "duplicate", "order_id": order_id}
        self.idempotency_cache.add(order_id)
        try:
            result = await self.broker.place_order(order)
            if result.get('status') == 'executed':
                self.config['risk_engine'].add_position(result)
            return result
        except Exception as e:
            for attempt in range(3):
                await asyncio.sleep(1)
                try:
                    result = await self.broker.place_order(order)
                    return result
                except:
                    continue
            return {"status": "failed", "error": str(e)}
