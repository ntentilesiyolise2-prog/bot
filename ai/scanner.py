import asyncio
import pandas as pd
from .vision.openrouter_scanner import OpenRouterVisionScanner
from .models.lstm_predictor import PricePredictor
from features.store import FeatureStore
from strategies.adaptive_swarm import AdaptiveSwarm
from utils.logger import setup_logger

logger = setup_logger(__name__)

class NexusScanner:
    def __init__(self):
        self.vision_scanner = OpenRouterVisionScanner()
        self.lstm = PricePredictor()
        self.feature_store = None
        self.strategy_swarm = None
        self.last_results = {}

    async def initialize(self, app_state):
        self.feature_store = app_state.feature_store
        self.strategy_swarm = app_state.strategy_swarm
        logger.info("NexusScanner initialized")

    async def scan(self, symbol, timeframe, df):
        if df.empty or self.feature_store is None:
            return None

        # Compute features
        features = await self.feature_store.compute_features(symbol, timeframe)
        if features.empty:
            return None

        # Get strategy votes
        result = self.strategy_swarm.get_votes(features)
        
        # Get LSTM prediction
        try:
            pred = self.lstm.predict_next(df)
            if pred:
                result['prediction'] = pred
        except Exception as e:
            logger.debug(f"LSTM prediction failed: {e}")

        # Generate explanation
        result['symbol'] = symbol
        result['timeframe'] = timeframe
        result['explanation'] = f"Swarm: {result['direction']} with {result['confluence']}% confluence."
        
        # Generate overlays
        result['overlays'] = self._generate_overlays(features)
        
        self.last_results[symbol] = result
        return result

    def _generate_overlays(self, features):
        # Placeholder for ICT overlays
        return {
            'order_blocks': [],
            'fvg': [],
            'liquidity_sweeps': [],
            'killzones': []
        }

    async def scan_image(self, image_bytes, symbol, timeframe):
        # Run OpenRouter vision
        vision_result = await self.vision_scanner.scan(image_bytes)
        if vision_result and 'error' not in vision_result:
            return {
                'symbol': symbol,
                'direction': vision_result.get('direction', 'neutral'),
                'confluence': vision_result.get('confidence', 50),
                'explanation': vision_result.get('explanation', 'No explanation'),
                'overlays': {}
            }
        return None
