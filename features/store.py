import pandas as pd
from .technical import add_technical_features
from .ict_smc import add_ict_features
from data.fabric import DataFabric
from utils.logger import setup_logger

logger = setup_logger(__name__)

class FeatureStore:
    def __init__(self, data_fabric: DataFabric):
        self.data_fabric = data_fabric

    async def compute_features(self, symbol: str, timeframe: str) -> pd.DataFrame:
        df = await self.data_fabric.get_candles(symbol, timeframe, limit=500)
        if df.empty:
            return df
        df = add_technical_features(df)
        df = add_ict_features(df)
        return df
