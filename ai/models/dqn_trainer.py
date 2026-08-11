import torch
import numpy as np
import pandas as pd
from .dqn_agent import DQNAgent
from data.fabric import DataFabric
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DQNTrainer:
    def __init__(self):
        self.agent = DQNAgent()
        self.state_size = 10
        self.action_size = 3
        self.fabric = DataFabric()

    async def train(self, symbol="BTCUSD", episodes=100):
        # Fetch historical data
        df = await self.fabric.get_candles(symbol, "M15", limit=1000)
        if df.empty:
            return
        # Convert to features
        features = ['Open','High','Low','Close','Volume','rsi_14','atr_14','adx']
        # Assume we have these features (we will compute them in the loop)
        # For each episode, simulate trading
        for ep in range(episodes):
            state = self._get_state(df, 0)
            done = False
            step = 0
            total_reward = 0
            while not done and step < len(df) - 10:
                action = self.agent.act(state)
                # Simulate action: BUY (0), SELL (1), HOLD (2)
                if action == 0:
                    # Simulate buy at current price, sell after 5 steps
                    entry = df.iloc[step]['Close']
                    exit_price = df.iloc[step+5]['Close'] if step+5 < len(df) else entry
                    reward = (exit_price - entry) * 100
                elif action == 1:
                    entry = df.iloc[step]['Close']
                    exit_price = df.iloc[step+5]['Close'] if step+5 < len(df) else entry
                    reward = (entry - exit_price) * 100
                else:
                    reward = 0
                next_state = self._get_state(df, step+1)
                self.agent.remember(state, action, reward, next_state, done)
                state = next_state
                total_reward += reward
                step += 1
                if step >= len(df) - 10:
                    done = True
            # Replay after episode
            self.agent.replay()
            if ep % 10 == 0:
                logger.info(f"Episode {ep}, Total Reward: {total_reward:.2f}")
        # Save weights
        torch.save(self.agent.model.state_dict(), "models/dqn_weights.pth")
        logger.info("DQN training complete.")

    def _get_state(self, df, idx):
        # Build state vector from features
        if idx + 9 >= len(df):
            idx = len(df) - 10
        features = ['rsi_14','atr_14','adx','Close','Volume']
        state = []
        for i in range(10):
            row = df.iloc[idx+i]
            for f in features:
                val = row.get(f, 0)
                state.append(val)
        return np.array(state)
