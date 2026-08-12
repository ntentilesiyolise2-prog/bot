import random
from datetime import datetime
from utils.journal import TradeJournal
from utils.logger import setup_logger

logger = setup_logger(__name__)

class Simulator:
    def __init__(self):
        self.balance = 10000.0
        self.positions = []
        self.journal = TradeJournal()  # <-- Journal integrated

    async def connect(self):
        logger.info("Simulator connected.")

    async def disconnect(self):
        logger.info("Simulator disconnected.")

    async def place_order(self, order):
        symbol = order['symbol']
        side = order['side']
        lot = float(order['lot'])
        price = order.get('price', 100.0)
        slippage = random.uniform(-0.01, 0.01)
        fill_price = price + slippage

        position = {
            'id': random.randint(1000, 9999),
            'symbol': symbol,
            'side': side,
            'lot': lot,
            'entry_price': fill_price,
            'current_price': fill_price,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.positions.append(position)

        # Save to journal
        self.journal.add_trade({
            'symbol': symbol,
            'side': side,
            'entry': fill_price,
            'exit': fill_price,
            'pnl': 0,
            'source': 'bot',
            'order_id': position['id'],
            'status': 'open'
        })

        logger.info(f"Simulator: {side} {lot} {symbol} @ {fill_price}")
        return {
            "status": "executed",
            "id": position['id'],
            "symbol": symbol,
            "side": side,
            "lot": lot,
            "price": fill_price
        }

    async def close_position(self, position):
        # Update current price (simulate market move)
        current_price = position['entry_price'] * (1 + random.uniform(-0.02, 0.02))
        position['current_price'] = current_price
        entry = position['entry_price']
        lot = position['lot']
        side = position['side']
        if side == 'BUY':
            pnl = (current_price - entry) * lot * 100
        else:
            pnl = (entry - current_price) * lot * 100

        # Remove from open positions
        self.positions = [p for p in self.positions if p['id'] != position['id']]

        # Update journal with final PnL
        self.journal.add_trade({
            'symbol': position['symbol'],
            'side': position['side'],
            'entry': entry,
            'exit': current_price,
            'pnl': round(pnl, 2),
            'source': 'bot',
            'order_id': position['id'],
            'closed_at': datetime.utcnow().isoformat(),
            'status': 'closed'
        })

        logger.info(f"Simulator: Closed {position['symbol']} PnL: {pnl:.2f}")
        return {"status": "closed", "pnl": round(pnl, 2)}

    async def flatten_all(self):
        for pos in self.positions[:]:
            await self.close_position(pos)
        logger.info("All positions flattened.")
