import asyncio
import yfinance as yf
import pandas as pd
import numpy as np
from alpha_vantage.timeseries import TimeSeries
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
        self.alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.twelve_key = os.getenv("TWELVE_DATA_API_KEY")
        self._init_providers()
        self.binance_depth_cache = {}

    def _init_providers(self):
        self.providers = []
        self.providers.append(("yahoo", self._fetch_yahoo))
        if self.alpha_key:
            self.providers.append(("alpha_vantage", self._fetch_alpha_vantage))
        if self.twelve_key:
            self.providers.append(("twelve_data", self._fetch_twelve_data))
        logger.info(f"DataFabric initialized with {len(self.providers)} providers")

    async def get_candles(self, symbol, timeframe, limit=500):
        key = f"{symbol}_{timeframe}_{limit}"
        if key in self.cache:
            return self.cache[key]

        # Fetch from all providers in parallel
        tasks = []
        for name, provider in self.providers:
            tasks.append(self._safe_fetch(provider, symbol, timeframe, limit))
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect valid DataFrames
        dfs = []
        for res in results:
            if isinstance(res, pd.DataFrame) and not res.empty:
                dfs.append(res)

        if not dfs:
            logger.error(f"All providers failed for {symbol}")
            return pd.DataFrame()

        # Aggregate median
        # Align indices (time)
        # For simplicity, assume all have the same index (we'll reindex)
        # Use the most common index
        common_index = dfs[0].index
        for df in dfs[1:]:
            common_index = common_index.intersection(df.index)
        if len(common_index) < 2:
            # Fallback to first df
            self.cache[key] = dfs[0]
            return dfs[0]

        # Concatenate and compute median
        all_dfs = []
        for df in dfs:
            all_dfs.append(df.reindex(common_index))
        combined = pd.concat(all_dfs, axis=1, keys=[f"df{i}" for i in range(len(all_dfs))])
        # For each column, median across providers
        median_df = pd.DataFrame(index=common_index)
        for col in ['Open','High','Low','Close','Volume']:
            median_df[col] = combined.xs(col, axis=1, level=1).median(axis=1)
        self.cache[key] = median_df
        logger.debug(f"Fetched aggregated median candles for {symbol}")
        return median_df

    async def _safe_fetch(self, provider_func, symbol, timeframe, limit):
        try:
            return await provider_func(symbol, timeframe, limit)
        except Exception as e:
            logger.warning(f"Provider fetch error: {e}")
            return pd.DataFrame()

    # ---- Provider implementations (same as before) ----
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

    async def _fetch_twelve_data(self, symbol, timeframe, limit=500):
        if not self.twelve_key:
            raise ValueError("Twelve Data key missing")
        interval_map = {"M1":"1min", "M5":"5min", "M15":"15min", "M30":"30min",
                        "H1":"1h", "H4":"4h", "D1":"1day", "W1":"1week", "MN":"1month"}
        interval = interval_map.get(timeframe, "1day")
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={limit}&apikey={self.twelve_key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                if 'values' not in data:
                    raise ValueError("No data")
                df = pd.DataFrame(data['values'])
                df = df.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
                df = df[['Open','High','Low','Close','Volume']].astype(float)
                # Twelve data returns descending, reverse
                df = df.iloc[::-1]
                return df

    # ---- Forex tick, Binance depth, VIX term (unchanged) ----
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

    async def get_binance_depth(self, symbol="btcusdt"):
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
