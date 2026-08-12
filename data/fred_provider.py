import aiohttp
import os
import pandas as pd
from datetime import datetime, timedelta
from utils.logger import setup_logger

logger = setup_logger(__name__)

class FREDProvider:
    def __init__(self):
        self.api_key = os.getenv("FRED_API_KEY")
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"

    async def get_cpi(self):
        if not self.api_key:
            return None
        params = {
            "series_id": "CPIAUCSL",
            "api_key": self.api_key,
            "file_type": "json",
            "limit": 2
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        obs = data['observations']
                        if len(obs) >= 2:
                            latest = float(obs[-1]['value'])
                            prev = float(obs[-2]['value'])
                            return {"latest": latest, "change": latest - prev}
        except Exception as e:
            logger.error(f"FRED error: {e}")
        return None
