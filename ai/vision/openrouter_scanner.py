import aiohttp
import base64
import os
from utils.logger import setup_logger

logger = setup_logger(__name__)

class OpenRouterVisionScanner:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.enabled = bool(self.api_key)

    async def scan(self, image_bytes):
        if not self.enabled:
            return {"error": "OpenRouter API key missing. Set OPENROUTER_API_KEY in .env"}

        b64 = base64.b64encode(image_bytes).decode('utf-8')
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this candlestick chart. Identify patterns (engulfing, doji, head and shoulders, etc.). Give direction (bullish/bearish/neutral) and confidence (0-100)."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    ]
                }
            ],
            "max_tokens": 100
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        content = data['choices'][0]['message']['content']
                        direction = "neutral"
                        confidence = 50
                        if "bullish" in content.lower():
                            direction = "bullish"
                        elif "bearish" in content.lower():
                            direction = "bearish"
                        import re
                        match = re.search(r'(\d+)%', content)
                        if match:
                            confidence = int(match.group(1))
                        return {
                            "direction": direction,
                            "confidence": confidence,
                            "explanation": content
                        }
                    else:
                        logger.error(f"OpenRouter error: {await resp.text()}")
                        return {"error": "OpenRouter API error"}
        except Exception as e:
            logger.error(f"OpenRouter exception: {e}")
            return {"error": str(e)}
