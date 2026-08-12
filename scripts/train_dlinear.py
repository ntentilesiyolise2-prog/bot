#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import asyncio
import torch
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from ai.models.dlinear import DLinear
from data.fabric import DataFabric
from utils.logger import setup_logger

logger = setup_logger("DLinear_Trainer")

async def main():
    fabric = DataFabric()
    await fabric.initialize()
    symbols = ["BTCUSD", "ETHUSD", "EURUSD", "GBPUSD", "USDJPY"]
    seq_len = 60
    pred_len = 5

    for symbol in symbols:
        logger.info(f"Training DLinear on {symbol}...")
        df = await fabric.get_candles(symbol, "D1", limit=2000)
        if df.empty:
            continue

        # Prepare data
        scaler = MinMaxScaler()
        data = scaler.fit_transform(df[['Close']])
        X, y = [], []
        for i in range(len(data) - seq_len - pred_len):
            X.append(data[i:i+seq_len])
            y.append(data[i+seq_len:i+seq_len+pred_len])
        X = np.array(X).astype(np.float32)
        y = np.array(y).astype(np.float32)

        # Train model
        model = DLinear(seq_len=seq_len, pred_len=pred_len, enc_in=1)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = torch.nn.MSELoss()

        for epoch in range(50):
            epoch_loss = 0
            for i in range(0, len(X), 32):
                batch_x = torch.tensor(X[i:i+32])
                batch_y = torch.tensor(y[i:i+32])
                optimizer.zero_grad()
                pred = model(batch_x)
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            if epoch % 10 == 0:
                logger.info(f"  Epoch {epoch}, loss: {epoch_loss/len(X):.6f}")

        # Save model
        os.makedirs("models", exist_ok=True)
        torch.save(model.state_dict(), f"models/dlinear_{symbol}.pth")
        logger.info(f"✅ DLinear saved for {symbol}")

if __name__ == "__main__":
    asyncio.run(main())
