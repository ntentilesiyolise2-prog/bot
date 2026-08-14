import cv2
import numpy as np
import asyncio
import requests
from io import BytesIO
from PIL import Image
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MicroExpressionAnalyzer:
    def __init__(self):
        self.emotion_map = {
            'angry': -1, 'disgust': -1, 'fear': -0.8, 'sad': -0.6,
            'neutral': 0, 'surprise': 0.8, 'happy': 1.0
        }
        self.detected_sentiment = 0.0

    async def fetch_image(self, url):
        """Download an image from a URL (e.g., a news anchor frame)."""
        try:
            response = requests.get(url, timeout=5)
            img = Image.open(BytesIO(response.content))
            return np.array(img)
        except Exception as e:
            logger.error(f"Image fetch failed: {e}")
            return None

    async def analyze_anchor_sentiment(self, image_url):
        """Analyze a frame of a news anchor to detect sentiment before news."""
        img = await self.fetch_image(image_url)
        if img is None:
            return 0.0

        try:
            # Use DeepFace for emotion detection
            from deepface import DeepFace
            results = DeepFace.analyze(img, actions=['emotion'], enforce_detection=False)
            if results and isinstance(results, list):
                result = results[0]
                emotion = result.get('dominant_emotion')
                sentiment_score = self.emotion_map.get(emotion, 0)
                self.detected_sentiment = sentiment_score
                logger.info(f"Anchor Emotion: {emotion} -> Score: {sentiment_score}")
                return sentiment_score
        except ImportError:
            logger.warning("DeepFace not installed. Install with: pip install deepface tensorflow")
        except Exception as e:
            logger.error(f"Expression analysis failed: {e}")
        return 0.0

    def get_market_bias(self):
        """Map the emotion score to a market direction."""
        if self.detected_sentiment > 0.3:
            return "BULLISH"
        elif self.detected_sentiment < -0.3:
            return "BEARISH"
        return "NEUTRAL"
