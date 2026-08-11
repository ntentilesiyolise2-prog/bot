import pandas as pd
import yfinance as yf
import ccxt
import os
import json
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SymbolInfo:
    def __init__(self):
        self.cache_file = "symbols_cache.json"
        self.cache = self._load_cache()
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        self.yf = yf

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=4)

    def get_symbol_metadata(self, symbol):
        """Get metadata for ANY symbol (Forex, Crypto, Stocks, Indices, Commodities)."""
        if symbol in self.cache:
            return self.cache[symbol]

        metadata = self._fetch_from_broker(symbol)
        if not metadata:
            metadata = self._fetch_from_yahoo(symbol)

        if metadata:
            self.cache[symbol] = metadata
            self._save_cache()
            return metadata
        return None

    def _fetch_from_broker(self, symbol):
        # Try MT5 if available
        try:
            import MetaTrader5 as mt5
            if mt5.initialize():
                info = mt5.symbol_info(symbol)
                if info:
                    return {
                        'symbol': symbol,
                        'digits': info.digits,
                        'point': info.point,
                        'trade_mode': info.trade_mode,
                        'volume_min': info.volume_min,
                        'volume_max': info.volume_max,
                        'volume_step': info.volume_step,
                        'description': info.description,
                        'source': 'mt5'
                    }
        except:
            pass
        return None

    def _fetch_from_yahoo(self, symbol):
        try:
            ticker = self.yf.Ticker(symbol)
            info = ticker.info
            if info:
                return {
                    'symbol': symbol,
                    'digits': 2 if 'USD' in symbol else 4,
                    'point': 0.01 if 'USD' in symbol else 0.0001,
                    'trade_mode': 'full',
                    'volume_min': 0.01,
                    'volume_max': 1000,
                    'volume_step': 0.01,
                    'description': info.get('longName', symbol),
                    'source': 'yahoo'
                }
        except:
            pass
        return None

    def search_symbols(self, query):
        """Search for symbols matching the query (live from exchange)."""
        query = query.upper()
        results = []

        # Check cache first
        for sym in self.cache:
            if query in sym:
                results.append(self.cache[sym])

        # If not enough results, fetch from exchange
        if len(results) < 5:
            try:
                markets = self.exchange.load_markets()
                for sym in list(markets.keys())[:500]:  # Limit to 500 for speed
                    if query in sym.upper():
                        results.append({
                            'symbol': sym,
                            'digits': 4,
                            'point': 0.0001,
                            'source': 'binance'
                        })
                        if len(results) >= 20:
                            break
            except:
                pass

        return results[:20]
