import asyncio
import pandas as pd
from ai.models.lstm_predictor import PricePredictor
from ai.models.dqn_agent import DQNAgent
from ai.models.dqn_trainer import DQNTrainer
from utils.logger import setup_logger

logger = setup_logger(__name__)

class OnlineRetrainer:
    def __init__(self, app_state):
        self.app = app_state
        self.lstm = PricePredictor()
        self.dqn = DQNAgent()
        self.last_retrain = None

    async def retrain(self):
        logger.info("Starting online retraining...")
        # Fetch recent data
        df = await self.app.data_fabric.get_candles('BTCUSD', 'D1', limit=500)
        if df.empty:
            return
        # Retrain LSTM
        self.lstm.train(df, epochs=5)
        # Retrain DQN (simplified)
        trainer = DQNTrainer()
        await trainer.train(episodes=10)
        self.last_retrain = pd.Timestamp.now()
        logger.info("Online retraining complete.")
