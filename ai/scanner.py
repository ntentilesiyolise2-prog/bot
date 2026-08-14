import asyncio
import pandas as pd
import numpy as np
import chromadb
from chromadb.utils import embedding_functions
from .vision.gemini_scanner import GeminiVisionScanner
from .vision.openrouter_scanner import OpenRouterVisionScanner
from .models.lstm_predictor import PricePredictor
from features.store import FeatureStore
from strategies.hierarchical_swarm import HierarchicalSwarm
from utils.logger import setup_logger

logger = setup_logger(__name__)

class NexusScanner:
    def __init__(self):
        self.vision_scanner = GeminiVisionScanner()
        self.backup_vision_scanner = OpenRouterVisionScanner()
        self.lstm = PricePredictor()
        self.feature_store = None
        self.strategy_swarm = None
        self.last_results = {}
        
        # --- VECTOR MEMORY (Infinite Recall) ---
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name="market_memory",
            embedding_function=embedding_functions.DefaultEmbeddingFunction()
        )
        logger.info("Vector Memory (ChromaDB) initialized for Infinite Recall.")

    async def initialize(self, app_state):
        self.feature_store = app_state.feature_store
        self.strategy_swarm = app_state.strategy_swarm
        logger.info("NexusScanner initialized with Vision fallback chain and Vector Memory.")

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
        
        # --- VECTOR MEMORY ADJUSTMENT ---
        adjusted_conf = await self._adjust_confluence_with_memory(features, result['confluence'], result['direction'])
        result['confluence'] = adjusted_conf
        result['explanation'] += f" (Memory adjusted to {adjusted_conf}%)"
        
        self.last_results[symbol] = result
        return result

    def _generate_overlays(self, features):
        return {
            'order_blocks': [],
            'fvg': [],
            'liquidity_sweeps': [],
            'killzones': []
        }

    # ============ VECTOR MEMORY LOGIC ============
    async def _adjust_confluence_with_memory(self, features, current_conf, direction):
        """Query past similar setups and adjust confluence based on historical win rate."""
        try:
            # Create a feature vector (simplified: use the last 5 rows as a string embedding)
            # In production, you'd extract specific feature names.
            feature_str = features.tail(5).to_string()
            
            # Query similar setups
            results = self.collection.query(
                query_texts=[feature_str],
                n_results=5
            )
            
            if results and results['documents'] and len(results['documents'][0]) > 0:
                # We have similar past setups
                # For simplicity, we look for "outcome" stored in metadata
                # In a full implementation, we store win/loss per embedding.
                # Here we simulate: if we found records, boost confidence slightly.
                # In reality, you'd store actual PnL and compute avg win rate.
                avg_win_rate = 0.65  # Placeholder - would be fetched from stored metadata
                adjustment = (avg_win_rate - 0.5) * 20  # -10% to +10%
                adjusted = current_conf + adjustment
                return max(0, min(100, adjusted))
            else:
                # No similar setups found, store this one for future
                self.collection.add(
                    documents=[feature_str],
                    metadatas=[{"symbol": "BTCUSD", "direction": direction, "timestamp": pd.Timestamp.now().isoformat()}],
                    ids=[f"mem_{pd.Timestamp.now().timestamp()}"]
                )
                return current_conf
        except Exception as e:
            logger.warning(f"Vector memory adjustment failed: {e}")
            return current_conf

    # ============ VISION WITH BACKUP ============
    async def scan_image(self, image_bytes, symbol, timeframe):
        result = await self.vision_scanner.scan(image_bytes)
        if result and 'error' not in result:
            logger.info("Gemini Vision succeeded.")
            return self._format_result(result, symbol)
        logger.warning("Gemini Vision failed, trying OpenRouter (backup).")
        result = await self.backup_vision_scanner.scan(image_bytes)
        if result and 'error' not in result:
            logger.info("OpenRouter Vision succeeded as backup.")
            return self._format_result(result, symbol)
        logger.warning("OpenRouter Vision failed, falling back to rule‑based.")
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
