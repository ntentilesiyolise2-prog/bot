import asyncio
import pandas as pd
from .vision.gemini_scanner import GeminiVisionScanner
from .models.lstm_predictor import PricePredictor
from features.store import FeatureStore
from strategies.adaptive_swarm import AdaptiveSwarm
from utils.logger import setup_logger

logger = setup_logger(__name__)

class NexusScanner:
    def __init__(self):
        self.vision_scanner = GeminiVisionScanner()  # Uses Gemini for chart analysis
        self.lstm = PricePredictor()
        self.feature_store = None
        self.strategy_swarm = None
        self.last_results = {}

    async def initialize(self, app_state):
        self.feature_store = app_state.feature_store
        self.strategy_swarm = app_state.strategy_swarm
        logger.info("NexusScanner initialized with Gemini Vision.")

    async def scan(self, symbol, timeframe, df):
        if df.empty or self.feature_store is None:
            return None

        features = await self.feature_store.compute_features(symbol, timeframe)
        if features.empty:
            return None

        result = self.strategy_swarm.get_votes(features)
        
        try:
            pred = self.lstm.predict_next(df)
            if pred:
                result['prediction'] = pred
        except Exception as e:
            logger.debug(f"LSTM prediction failed: {e}")

        result['symbol'] = symbol
        result['timeframe'] = timeframe
        result['explanation'] = f"Swarm: {result['direction']} with {result['confluence']}% confluence."
        result['overlays'] = self._generate_overlays(features)
        
        self.last_results[symbol] = result
        return result

    def _generate_overlays(self, features):
        # Placeholder for future ICT overlays
        return {
            'order_blocks': [],
            'fvg': [],
            'liquidity_sweeps': [],
            'killzones': []
        }

    async def scan_image(self, image_bytes, symbol, timeframe):
        """Scan a chart image using Gemini Vision and return a detailed signal."""
        result = await self.vision_scanner.scan(image_bytes)
        if result and 'error' not in result:
            return {
                'symbol': symbol,
                'direction': result.get('direction', 'NEUTRAL'),
                'confluence': result.get('confidence', 50),
                'explanation': result.get('explanation', 'No explanation'),
                'setup_grade': result.get('setup_grade', 'B'),
                'risk_reward': result.get('risk_reward', 'N/A'),
                'entry': result.get('entry'),
                'take_profit': result.get('take_profit'),
                'stop_loss': result.get('stop_loss'),
                'invalidation': result.get('invalidation'),
                'patterns': result.get('patterns', []),
                'overlays': {}
            }
        # Fallback to rule‑based (no AI vision)
        logger.warning("Gemini vision failed, falling back to rule‑based scanner.")
        return {
            'symbol': symbol,
            'direction': 'NEUTRAL',
            'confluence': 50,
            'explanation': 'Rule‑based fallback (no AI vision)',
            'setup_grade': 'C',
            'risk_reward': 'N/A',
            'entry': None,
            'take_profit': None,
            'stop_loss': None,
            'invalidation': None,
            'patterns': [],
            'overlays': {}
        }
