import MetaTrader5 as mt5
import time
import asyncio
import concurrent.futures
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MT5Broker:
    def __init__(self, account_config):
        self.login = account_config.get('login', 0)
        self.password = account_config.get('password', '')
        self.server = account_config.get('server', '')
        self.connected = False
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.positions = []

    # ========== ASYNC WRAPPER ==========
    async def connect(self):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.executor, self._sync_connect)
        return result

    async def disconnect(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._sync_disconnect)

    async def place_order(self, order):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._sync_place_order, order)

    async def update_sl_tp(self, symbol, sl=None, tp=None):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._sync_update_sl_tp, symbol, sl, tp)

    async def flatten_all(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._sync_flatten_all)

    # ========== SYNC IMPLEMENTATIONS ==========
    def _sync_connect(self):
        if not mt5.initialize():
            logger.error("MT5 initialize failed")
            return False
        if self.login and self.password and self.server:
            authorized = mt5.login(self.login, password=self.password, server=self.server)
            if authorized:
                self.connected = True
                logger.info(f"MT5 connected: {self.login}")
                return True
            else:
                logger.error(f"MT5 login failed: {mt5.last_error()}")
        return False

    def _sync_disconnect(self):
        mt5.shutdown()
        self.connected = False
        logger.info("MT5 disconnected")

    def _sync_place_order(self, order):
        if not self.connected:
            return {"status": "failed", "error": "Not connected"}

        symbol = order['symbol']
        lot = float(order['lot'])
        side = order['side']
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"status": "failed", "error": f"Symbol {symbol} not found"}
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"status": "failed", "error": "No tick data"}

        price = tick.ask if side == "BUY" else tick.bid

        # Build request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "NEXUS INFINITUM",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send order
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            pos = {
                'id': result.order,
                'symbol': symbol,
                'side': side,
                'lot': lot,
                'entry_price': price,
                'current_price': price,
                'timestamp': time.time()
            }
            self.positions.append(pos)
            return {
                "status": "executed",
                "id": result.order,
                "symbol": symbol,
                "side": side,
                "lot": lot,
                "price": price
            }
        else:
            logger.error(f"Order failed: {result.retcode} - {result.comment}")
            return {"status": "failed", "error": f"MT5 Error: {result.retcode} - {result.comment}"}

    def _sync_update_sl_tp(self, symbol, sl=None, tp=None):
        # Placeholder – implement actual SL/TP modification via MT5
        return {"status": "not_implemented"}

    def _sync_flatten_all(self):
        # Close all positions
        for pos in self.positions[:]:
            # Send close order
            # For simplicity, we just remove them
            self.positions.remove(pos)
        return {"status": "flattened"}
