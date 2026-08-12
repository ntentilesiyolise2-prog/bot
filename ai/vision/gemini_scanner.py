import os
import base64
import json
import re
import google.generativeai as genai
import PIL.Image
import io
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
        if not self.enabled:
            return {"error": "Gemini API key missing. Set GEMINI_API_KEY in environment."}

        try:
            image = PIL.Image.open(io.BytesIO(image_bytes))
            
            # Enhanced prompt for detailed analysis
            prompt = (
                "Analyze this candlestick chart and provide a detailed trading signal. "
                "Respond in valid JSON format with the following fields:\n"
                "{\n"
                "  \"direction\": \"BUY\" or \"SELL\" or \"NEUTRAL\",\n"
                "  \"confidence\": 0-100 (integer),\n"
                "  \"patterns\": [\"list of detected patterns\"],\n"
                "  \"setup_grade\": \"A\", \"B\", or \"C\" (A = highest confluence),\n"
                "  \"risk_reward\": \"2.7\" (example ratio),\n"
                "  \"entry\": \"4411.96\" (key price),\n"
                "  \"take_profit\": \"4393.65\",\n"
                "  \"stop_loss\": \"4420.07\",\n"
                "  \"invalidation\": \"Candle close above 4420.07\",\n"
                "  \"explanation\": \"Brief reason for the signal (1-2 sentences)\"\n"
                "}\n"
                "If any field is not applicable, use null. Be concise and professional."
            )
            
            response = self.model.generate_content([prompt, image])
            response_text = response.text.strip()

            # Parse JSON from response
            try:
                # Extract JSON block
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = response_text[start:end]
                    data = json.loads(json_str)
                    # Ensure required fields exist
                    return {
                        "direction": data.get("direction", "NEUTRAL"),
                        "confidence": data.get("confidence", 50),
                        "patterns": data.get("patterns", []),
                        "setup_grade": data.get("setup_grade", "B"),
                        "risk_reward": data.get("risk_reward", "N/A"),
                        "entry": data.get("entry", None),
                        "take_profit": data.get("take_profit", None),
                        "stop_loss": data.get("stop_loss", None),
                        "invalidation": data.get("invalidation", None),
                        "explanation": data.get("explanation", "No explanation provided."),
                        "raw": response_text
                    }
                else:
                    # Fallback: parse plain text
                    direction = "NEUTRAL"
                    confidence = 50
                    if "bullish" in response_text.lower():
                        direction = "BUY"
                    elif "bearish" in response_text.lower():
                        direction = "SELL"
                    return {
                        "direction": direction,
                        "confidence": confidence,
                        "patterns": [],
                        "setup_grade": "B",
                        "risk_reward": "N/A",
                        "entry": None,
                        "take_profit": None,
                        "stop_loss": None,
                        "invalidation": None,
                        "explanation": response_text[:200],
                        "raw": response_text
                    }
            except Exception as e:
                logger.error(f"Gemini response parsing error: {e}")
                return {"error": "Failed to parse Gemini response", "raw": response_text}

        except Exception as e:
            logger.error(f"Gemini vision error: {e}")
            return {"error": str(e)}
