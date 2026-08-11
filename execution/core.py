import uuid
import asyncio
from .simulator import Simulator

class ExecutionCore:
    def __init__(self, config):
        self.config = config
        self.broker = Simulator()
        self.idempotency_cache = set()
        self.pending_orders = []

    async def initialize(self):
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
            return result
        except Exception as e:
            # Retry logic
            for attempt in range(3):
                await asyncio.sleep(1)
                try:
                    result = await self.broker.place_order(order)
                    return result
                except:
                    continue
            return {"status": "failed", "error": str(e)}
