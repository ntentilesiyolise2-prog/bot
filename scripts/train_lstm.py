#!/usr/bin/env python3
"""
Train the LSTM predictor on historical data.
Run this manually once, or schedule it nightly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import asyncio
import pandas as pd
from data.fabric import DataFabric
from ai.models.lstm_predictor import PricePredictor
from utils.logger import setup_logger

logger = setup_logger("LSTM_Trainer")

async def main():
    fabric = DataFabric()
    await fabric.initialize()
    symbols = ["BTCUSD", "ETHUSD", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
    predictor = PricePredictor()

    for symbol in symbols:
        logger.info(f"Training LSTM on {symbol}...")
        df = await fabric.get_candles(symbol, "D1", limit=2000)  # 2000 daily candles
        if df.empty:
            logger.warning(f"No data for {symbol}")
            continue
        predictor.train(df, epochs=100)  # 100 epochs for decent accuracy
        logger.info(f"✅ LSTM trained on {symbol}")

    logger.info("All symbols trained. Weights saved.")

if __name__ == "__main__":
    asyncio.run(main())
