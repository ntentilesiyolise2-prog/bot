import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import os
from utils.logger import setup_logger

logger = setup_logger(__name__)

class LSTMPredictor(nn.Module):
    def __init__(self, input_size=5, hidden_size=64, num_layers=2, output_size=5):
        super(LSTMPredictor, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out

class PricePredictor:
    def __init__(self, seq_length=60):
        self.seq_length = seq_length
        self.model = None
        self.scaler = MinMaxScaler()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_path = "models/lstm_weights.pth"
        self._load_or_init()

    def _load_or_init(self):
        os.makedirs("models", exist_ok=True)
        self.model = LSTMPredictor().to(self.device)
        if os.path.exists(self.model_path):
            try:
                self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                logger.info("Loaded pre-trained LSTM model.")
            except:
                logger.warning("Failed to load LSTM model, initializing fresh.")
        else:
            logger.info("Initializing new LSTM model.")

    def prepare_data(self, df: pd.DataFrame):
        features = ['Open', 'High', 'Low', 'Close', 'Volume']
        data = df[features].values
        scaled = self.scaler.fit_transform(data)
        if len(scaled) < self.seq_length:
            return None
        seq = scaled[-self.seq_length:]
        return torch.tensor(seq, dtype=torch.float32).unsqueeze(0).to(self.device)

    def predict_next(self, df: pd.DataFrame):
        if df.empty or len(df) < self.seq_length:
            return None
        self.model.eval()
        with torch.no_grad():
            input_seq = self.prepare_data(df)
            if input_seq is None:
                return None
            output = self.model(input_seq)
            # Inverse transform
            dummy = np.zeros((output.shape[1], 5))
            dummy[:, 3] = output.cpu().numpy()[0]  # Close price index
            pred_prices = self.scaler.inverse_transform(dummy)[:, 3]
            return pred_prices.tolist()

    def train(self, df: pd.DataFrame, epochs=50):
        if df.empty:
            return
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        data = self.prepare_data(df)
        if data is None:
            return
        target = data[0, -5:, 3]  # Last 5 closes
        for epoch in range(epochs):
            optimizer.zero_grad()
            output = self.model(data)
            loss = criterion(output.squeeze(), target)
            loss.backward()
            optimizer.step()
        torch.save(self.model.state_dict(), self.model_path)
        logger.info(f"LSTM trained for {epochs} epochs.")
