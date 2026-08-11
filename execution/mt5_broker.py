import MetaTrader5 as mt5
import time
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MT5Broker:
    def __init__(self, account_config):
        self.login = account_config.get('login', 0)
        self.password = account_config.get('password', '')
        self.server = account_config.get('server', '')
        self.connected = False

    async def connect(self):
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
        else:
            logger.warning("MT5 credentials missing.")
        return False

    async def disconnect(self):
        mt5.shutdown()
        self.connected = False
        logger.info("MT5 disconnected")

    async def place_order(self, order):
        if not self.connected:
            return {"status": "failed", "error": "MT5 not connected"}
        symbol = order['symbol']
        lot = float(order['lot'])
        side = order['side']
        # Map side
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"status": "failed", "error": f"Symbol {symbol} not found"}
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"status": "failed", "error": "No tick data"}

        price = tick.ask if side == "BUY" else tick.bid
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
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.retcode}")
            return {"status": "failed", "error": f"MT5 Error: {result.retcode}"}
        return {
            "status": "executed",
            "id": result.order,
            "symbol": symbol,
            "side": side,
            "lot": lot,
            "price": price
        }
