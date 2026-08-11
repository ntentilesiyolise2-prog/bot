import asyncio
import pandas as pd
from .providers import YahooProvider, AlphaVantageProvider, PolygonProvider
from .cache import TTLSCache
from utils.logger import setup_logger
import os

logger = setup_logger(__name__)

class DataFabric:
    def __init__(self):
        self.cache = TTLSCache(default_ttl=30)
        self.providers = []
        self._init_providers()

    def _init_providers(self):
        # Yahoo is always available
        self.providers.append(YahooProvider())
        # Alpha Vantage
        av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if av_key:
            self.providers.append(AlphaVantageProvider(av_key))
        # Polygon
        poly_key = os.getenv("POLYGON_API_KEY")
        if poly_key:
            self.providers.append(PolygonProvider(poly_key))
        logger.info(f"DataFabric initialized with {len(self.providers)} providers")

    async def get_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        cache_key = f"{symbol}_{timeframe}_{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Try providers in order, fallback on failure
        for provider in self.providers:
            try:
                df = await provider.fetch_candles(symbol, timeframe, limit)
                if df is not None and not df.empty:
                    self.cache.set(cache_key, df)
                    logger.debug(f"Fetched {len(df)} candles from {provider.name}")
                    return df
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                provider.quality_score -= 10
                continue

        # If all providers fail, return empty DataFrame
        logger.error(f"All providers failed for {symbol}")
        return pd.DataFrame()
