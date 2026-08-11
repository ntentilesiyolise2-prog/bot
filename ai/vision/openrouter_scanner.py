import aiohttp
import base64
import os
from utils.logger import setup_logger

logger = setup_logger(__name__)

class OpenRouterVisionScanner:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.enabled = bool(self.api_key)

    async def scan(self, image_bytes: bytes) -> dict:
        if not self.enabled:
            return {"error": "OpenRouter API key missing. Please set OPENROUTER_API_KEY in .env"}

        # Encode image to base64
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4-vision-preview",  # or "claude-3-opus-20240229-vision"
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this candlestick chart. Identify patterns (e.g., engulfing, doji, head and shoulders). Estimate the likely direction (bullish, bearish, neutral). Give a confidence score (0-100) and a brief explanation."},
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
                        # Simple parsing
                        direction = "neutral"
                        confidence = 50
                        if "bullish" in content.lower():
                            direction = "bullish"
                        elif "bearish" in content.lower():
                            direction = "bearish"
                        # Extract confidence if present
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
