import asyncio
import pandas as pd
from .vision.gemini_scanner import GeminiVisionScanner
from .vision.openrouter_scanner import OpenRouterVisionScanner
from .models.lstm_predictor import PricePredictor
from features.store import FeatureStore
from strategies.hierarchical_swarm import HierarchicalSwarm
from utils.logger import setup_logger

logger = setup_logger(__name__)

class NexusScanner:
    def __init__(self):
        # Primary vision scanner (Gemini)
        self.vision_scanner = GeminiVisionScanner()
        # Backup vision scanner (OpenRouter)
        self.backup_vision_scanner = OpenRouterVisionScanner()
        self.lstm = PricePredictor()
        self.feature_store = None
        self.strategy_swarm = None
        self.last_results = {}

    async def initialize(self, app_state):
        self.feature_store = app_state.feature_store
        self.strategy_swarm = app_state.strategy_swarm
        logger.info("NexusScanner initialized with Vision fallback chain.")

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
        return {
            'order_blocks': [],
            'fvg': [],
            'liquidity_sweeps': [],
            'killzones': []
        }

    # ============== VISION WITH BACKUP ==============
    async def scan_image(self, image_bytes, symbol, timeframe):
        """
        Scan a chart image using:
        1. Gemini Vision (primary)
        2. OpenRouter Vision (backup)
        3. Rule‑based (final fallback)
        """
        # 1. Try Gemini Vision
        result = await self.vision_scanner.scan(image_bytes)
        if result and 'error' not in result:
            logger.info("Gemini Vision succeeded.")
            return self._format_result(result, symbol)

        logger.warning("Gemini Vision failed, trying OpenRouter (backup).")
        
        # 2. Try OpenRouter Vision
        result = await self.backup_vision_scanner.scan(image_bytes)
        if result and 'error' not in result:
            logger.info("OpenRouter Vision succeeded as backup.")
            return self._format_result(result, symbol)

        logger.warning("OpenRouter Vision failed, falling back to rule‑based.")
        
        # 3. Rule‑based fallback (no AI vision)
        return {
            'symbol': symbol,
            'direction': 'NEUTRAL',
            'confluence': 50,
            'explanation': 'Rule‑based fallback (AI vision unavailable)',
            'setup_grade': 'C',
            'risk_reward': 'N/A',
            'entry': None,
            'take_profit': None,
            'stop_loss': None,
            'invalidation': None,
            'patterns': [],
            'overlays': {}
        }

    def _format_result(self, result, symbol):
        """Format the vision result into a unified structure."""
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
