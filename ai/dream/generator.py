import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DreamGenerator:
    def __init__(self):
        self.scaler = MinMaxScaler()

    def generate(self, df: pd.DataFrame, num_samples=1000):
        """Generate synthetic market data based on the real data distribution."""
        if df.empty:
            return pd.DataFrame()
        # Take the last 100 candles to capture current regime
        base = df.tail(100)
        features = ['Open', 'High', 'Low', 'Close', 'Volume']
        data = base[features].values
        scaled = self.scaler.fit_transform(data)
        # Create synthetic sequences using random walks + noise
        synthetic = []
        for _ in range(num_samples):
            # Start from a random point in the sequence
            start_idx = np.random.randint(0, len(scaled) - 10)
            seq = scaled[start_idx:start_idx+10].copy()
            # Add random walk and noise
            for i in range(1, len(seq)):
                seq[i] += np.random.normal(0, 0.01, seq[i].shape)
            # Clamp to 0-1 range
            seq = np.clip(seq, 0, 1)
            synthetic.append(seq)
        # Flatten and inverse transform
        synthetic = np.array(synthetic)
        # Reshape to (samples * sequence_len, features)
        flat = synthetic.reshape(-1, 5)
        real_flat = self.scaler.inverse_transform(flat)
        # Reshape back
        result = real_flat.reshape(-1, 10, 5)
        logger.info(f"Generated {num_samples} synthetic samples.")
        return result
