import aiohttp
import os
import pandas as pd
from datetime import datetime, timedelta

class FREDProvider:
    def __init__(self):
        self.api_key = os.getenv("FRED_API_KEY")
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"

    async def get_cpi(self):
        """Fetch latest CPI data."""
        if not self.api_key:
            return None
        params = {
            "series_id": "CPIAUCSL",
            "api_key": self.api_key,
            "file_type": "json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    observations = data['observations']
                    return {
                        "latest": float(observations[-1]['value']),
                        "change": float(observations[-1]['value']) - float(observations[-2]['value'])
                    }
        return None
