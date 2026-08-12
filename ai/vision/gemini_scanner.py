import os
import base64
import google.generativeai as genai
from utils.logger import setup_logger

logger = setup_logger(__name__)

class GeminiVisionScanner:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.enabled = bool(self.api_key)
        if self.enabled:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            logger.info("Gemini Vision Scanner initialized.")
        else:
            logger.warning("GEMINI_API_KEY not set. Vision scanner disabled.")

    async def scan(self, image_bytes):
        """Analyze a chart image and return direction and confidence."""
        if not self.enabled:
            return {"error": "Gemini API key missing. Set GEMINI_API_KEY in environment."}

        try:
            # Encode image to base64
            b64 = base64.b64encode(image_bytes).decode('utf-8')
            # Construct prompt
            prompt = (
                "Analyze this candlestick chart. Identify patterns (engulfing, doji, head and shoulders, etc.). "
                "Give direction (bullish, bearish, or neutral) and a confidence score (0-100). "
                "Respond in JSON format: {\"direction\": \"bullish\", \"confidence\": 85, \"patterns\": [\"Bullish Engulfing\"]}"
            )
            # Gemini expects image as a PIL Image or bytes
            import PIL.Image
            import io
            image = PIL.Image.open(io.BytesIO(image_bytes))
            
            response = self.model.generate_content([prompt, image])
            response_text = response.text.strip()
            
            # Try to parse JSON
            import json
            try:
                # Find JSON block in response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = response_text[start:end]
                    data = json.loads(json_str)
                    direction = data.get('direction', 'neutral')
                    confidence = data.get('confidence', 50)
                    patterns = data.get('patterns', [])
                    return {
                        "direction": direction,
                        "confidence": confidence,
                        "patterns": patterns,
                        "raw": response_text
                    }
                else:
                    # Fallback: parse plain text
                    direction = "neutral"
                    confidence = 50
                    if "bullish" in response_text.lower():
                        direction = "bullish"
                    elif "bearish" in response_text.lower():
                        direction = "bearish"
                    return {
                        "direction": direction,
                        "confidence": confidence,
                        "patterns": [],
                        "raw": response_text
                    }
            except Exception as e:
                logger.error(f"Gemini response parsing error: {e}")
                return {"error": "Failed to parse Gemini response", "raw": response_text}

        except Exception as e:
            logger.error(f"Gemini vision error: {e}")
            return {"error": str(e)}
