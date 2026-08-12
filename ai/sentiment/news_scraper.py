import aiohttp
import asyncio
from transformers import pipeline
from utils.logger import setup_logger

logger = setup_logger(__name__)

class NewsSentiment:
    def __init__(self):
        try:
            self.classifier = pipeline('sentiment-analysis', model='yiyanghkust/finbert-tone', device=-1)
        except:
            self.classifier = None
        self.cache = {}

    async def fetch_news(self, symbol):
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        import re
                        titles = re.findall(r'<title>(.*?)</title>', text)
                        return titles[1:6]
        except:
            return []
        return []

    async def get_sentiment(self, symbol):
        headlines = await self.fetch_news(symbol)
        if not headlines:
            return {"sentiment": "neutral", "score": 0.0, "headlines": []}
        if self.classifier is None:
            return {"sentiment": "neutral", "score": 0.0, "headlines": headlines}
        results = self.classifier(headlines)
        score = sum(r['score'] if r['label'] == 'Positive' else -r['score'] for r in results) / len(results)
        sentiment = 'bullish' if score > 0.2 else 'bearish' if score < -0.2 else 'neutral'
        return {"sentiment": sentiment, "score": round(score, 3), "headlines": headlines}
