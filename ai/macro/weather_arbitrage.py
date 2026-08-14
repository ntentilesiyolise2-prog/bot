import aiohttp
import os
from utils.logger import setup_logger

logger = setup_logger(__name__)

class WeatherArbitrage:
    def __init__(self):
        self.api_key = os.getenv("WEATHER_API_KEY")  # Free from OpenWeatherMap
        self.last_temp = None

    async def get_forecast(self, city="New York"):
        if not self.api_key:
            logger.warning("WEATHER_API_KEY not set. Weather arbitrage disabled.")
            return None
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        temp = data['main']['temp']
                        self.last_temp = temp
                        logger.info(f"Weather in {city}: {temp}°C")
                        return temp
                    else:
                        logger.error(f"Weather API error: {resp.status}")
        except Exception as e:
            logger.error(f"Weather API error: {e}")
        return None

    def get_trade_signal(self, temp=None):
        if temp is None:
            temp = self.last_temp
        if temp is None:
            return None
        # If extreme cold (< -5°C), natural gas demand rises (BUY Natural Gas)
        if temp < -5:
            return {'symbol': 'NGAS', 'direction': 'BUY', 'confluence': 85, 'explanation': 'Extreme cold increases gas demand'}
        # If extreme heat (> 35°C), energy demand rises (BUY Oil)
        elif temp > 35:
            return {'symbol': 'OIL', 'direction': 'BUY', 'confluence': 80, 'explanation': 'Heatwave increases energy demand'}
        else:
            return None
