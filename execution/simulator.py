import random
from datetime import datetime

class Simulator:
    def __init__(self):
        self.balance = 10000.0
        self.positions = []

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def place_order(self, order):
        price = order.get('price', 100.0)
        slippage = random.uniform(-0.01, 0.01)
        fill_price = price + slippage
        pos = {
            'id': random.randint(1000, 9999),
            'symbol': order['symbol'],
            'side': order['side'],
            'lot': order['lot'],
            'entry_price': fill_price,
            'current_price': fill_price,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.positions.append(pos)
        return pos
