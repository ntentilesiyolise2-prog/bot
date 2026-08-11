import yfinance as yf
import pandas as pd
from alpha_vantage.timeseries import TimeSeries
from polygon import RESTClient
import os
import aiohttp
import asyncio
from datetime import datetime, timedelta
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DataProvider:
    def __init__(self, name: str):
        self.name = name
        self.quality_score = 100
        self.last_error = None

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        raise NotImplementedError

class YahooProvider(DataProvider):
    def __init__(self):
        super().__init__("yahoo")

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        interval_map = {"M1":"1m", "M5":"5m", "M15":"15m", "M30":"30m",
                        "H1":"1h", "H4":"1h", "D1":"1d", "W1":"1wk", "MN":"1mo"}
        interval = interval_map.get(timeframe, "1d")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="max", interval=interval)
        if len(df) > limit:
            df = df.tail(limit)
        if df.empty:
            raise ValueError("Empty data from Yahoo")
        return df[['Open','High','Low','Close','Volume']]

class AlphaVantageProvider(DataProvider):
    def __init__(self, api_key: str):
        super().__init__("alpha_vantage")
        self.api_key = api_key
        self.client = TimeSeries(key=self.api_key, output_format='pandas')

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        interval_map = {"M1":"1min", "M5":"5min", "M15":"15min", "M30":"30min",
                        "H1":"60min", "H4":"60min", "D1":"daily", "W1":"weekly", "MN":"monthly"}
        interval = interval_map.get(timeframe, "daily")
        data, meta = self.client.get_intraday(symbol=symbol, interval=interval, outputsize='compact')
        if data.empty:
            raise ValueError("Empty data from Alpha Vantage")
        df = data.iloc[::-1].tail(limit)
        df.columns = ['Open','High','Low','Close','Volume']
        return df

class PolygonProvider(DataProvider):
    def __init__(self, api_key: str):
        super().__init__("polygon")
        self.api_key = api_key
        self.client = RESTClient(self.api_key)

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        timespan_map = {"M1":"minute", "M5":"minute", "M15":"minute", "M30":"minute",
                        "H1":"hour", "H4":"hour", "D1":"day", "W1":"week", "MN":"month"}
        multiplier = {"M1":1, "M5":5, "M15":15, "M30":30, "H1":1, "H4":4, "D1":1, "W1":1, "MN":1}
        end = datetime.now()
        start = end - timedelta(days=30)
        try:
            resp = self.client.stocks_equities_aggs(symbol, multiplier.get(timeframe,1), timespan_map.get(timeframe,"day"), start, end, limit=limit)
            if not resp:
                raise ValueError("Empty data from Polygon")
            df = pd.DataFrame([{'Open': a.open, 'High': a.high, 'Low': a.low, 'Close': a.close, 'Volume': a.volume} for a in resp])
            return df
        except Exception as e:
            raise e
