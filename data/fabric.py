import asyncio
import yfinance as yf
import pandas as pd
import numpy as np
from alpha_vantage.timeseries import TimeSeries
from polygon import RESTClient
import aiohttp
import os
import json
import websockets
from datetime import datetime, timedelta
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DataFabric:
    def __init__(self):
        self.cache = {}
        self.providers = []
        self.alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.polygon_key = os.getenv("POLYGON_API_KEY")
        self._init_providers()
        self.binance_depth_cache = {}

    def _init_providers(self):
        # Always have Yahoo
        self.providers.append(("yahoo", self._fetch_yahoo))
        if self.alpha_key:
            self.providers.append(("alpha_vantage", self._fetch_alpha_vantage))
        if self.polygon_key:
            self.providers.append(("polygon", self._fetch_polygon))
        logger.info(f"DataFabric initialized with {len(self.providers)} providers")

    # ==================== CANDLESTICK DATA ====================
    async def get_candles(self, symbol, timeframe, limit=500):
        key = f"{symbol}_{timeframe}_{limit}"
        if key in self.cache:
            return self.cache[key]

        # Try providers in order
        for name, provider in self.providers:
            try:
                df = await provider(symbol, timeframe, limit)
                if df is not None and not df.empty:
                    self.cache[key] = df
                    logger.debug(f"Fetched {len(df)} candles from {name}")
                    return df
            except Exception as e:
                logger.warning(f"Provider {name} failed: {e}")
                continue

        logger.error(f"All providers failed for {symbol}")
        return pd.DataFrame()

    async def _fetch_yahoo(self, symbol, timeframe, limit=500):
        interval_map = {"M1":"1m", "M5":"5m", "M15":"15m", "M30":"30m",
                        "H1":"1h", "H4":"1h", "D1":"1d", "W1":"1wk", "MN":"1mo"}
        interval = interval_map.get(timeframe, "1d")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="max", interval=interval)
        if len(df) > limit:
            df = df.tail(limit)
        if df.empty:
            raise ValueError("Empty data")
        return df[['Open','High','Low','Close','Volume']]

    async def _fetch_alpha_vantage(self, symbol, timeframe, limit=500):
        if not self.alpha_key:
            raise ValueError("AV key missing")
        ts = TimeSeries(key=self.alpha_key, output_format='pandas')
        interval_map = {"M1":"1min", "M5":"5min", "M15":"15min", "M30":"30min",
                        "H1":"60min", "H4":"60min", "D1":"daily", "W1":"weekly", "MN":"monthly"}
        interval = interval_map.get(timeframe, "daily")
        data, meta = ts.get_intraday(symbol=symbol, interval=interval, outputsize='compact')
        if data.empty:
            raise ValueError("Empty data")
        df = data.iloc[::-1].tail(limit)
        df.columns = ['Open','High','Low','Close','Volume']
        return df

    async def _fetch_polygon(self, symbol, timeframe, limit=500):
        if not self.polygon_key:
            raise ValueError("Polygon key missing")
        client = RESTClient(self.polygon_key)
        timespan_map = {"M1":"minute", "M5":"minute", "M15":"minute", "M30":"minute",
                        "H1":"hour", "H4":"hour", "D1":"day", "W1":"week", "MN":"month"}
        multiplier = {"M1":1, "M5":5, "M15":15, "M30":30, "H1":1, "H4":4, "D1":1, "W1":1, "MN":1}
        end = datetime.now()
        start = end - timedelta(days=30)
        try:
            resp = client.stocks_equities_aggs(symbol, multiplier.get(timeframe,1), timespan_map.get(timeframe,"day"), start, end, limit=limit)
            if not resp:
                raise ValueError("Empty data")
            df = pd.DataFrame([{'Open': a.open, 'High': a.high, 'Low': a.low, 'Close': a.close, 'Volume': a.volume} for a in resp])
            return df
        except Exception as e:
            raise e

    # ==================== FOREX TICK (ALPHA VANTAGE) ====================
    async def get_forex_tick(self, symbol):
        if not self.alpha_key:
            return None, None
        from_currency = symbol[:3]
        to_currency = symbol[3:]
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_currency}&to_currency={to_currency}&apikey={self.alpha_key}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if 'Realtime Currency Exchange Rate' in data:
                            bid = float(data['Realtime Currency Exchange Rate']['Bid Price'])
                            ask = float(data['Realtime Currency Exchange Rate']['Ask Price'])
                            return bid, ask
        except Exception as e:
            logger.error(f"Forex tick error: {e}")
        return None, None

    # ==================== BINANCE DEPTH (CRYPTO) ====================
    async def get_binance_depth(self, symbol="btcusdt"):
        # Returns cached depth snapshot
        return self.binance_depth_cache.get(symbol, {})

    async def start_binance_depth_stream(self, symbols=['btcusdt', 'ethusdt']):
        for sym in symbols:
            asyncio.create_task(self._listen_depth(sym))

    async def _listen_depth(self, symbol):
        ws_url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@depth20@100ms"
        while True:
            try:
                async with websockets.connect(ws_url) as ws:
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        self.binance_depth_cache[symbol] = data
            except Exception as e:
                logger.error(f"Binance depth error for {symbol}: {e}")
                await asyncio.sleep(5)

    # ==================== VIX TERM STRUCTURE ====================
    async def get_vix_term(self):
        try:
            vix = yf.Ticker("^VIX")
            vxv = yf.Ticker("^VXV")
            vix_spot = vix.history(period="1d")['Close'].iloc[-1]
            vix_future = vxv.history(period="1d")['Close'].iloc[-1]
            term = vix_future - vix_spot
            return term
        except:
            return 0.0
