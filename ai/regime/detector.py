import numpy as np
import pandas as pd

class RegimeDetector:
    def __init__(self):
        self.regime = 'neutral'
        self.thresholds = {
            'adx_trend': 25,
            'atr_volatility': 1.5,
            'rsi_oversold': 40,
            'rsi_overbought': 60
        }

    def detect(self, df):
        if df.empty or len(df) < 50:
            return 'neutral'
        atr = df['atr_14'].iloc[-1]
        adx = df['adx'].iloc[-1]
        rsi = df['rsi_14'].iloc[-1]
        atr_mean = df['atr_14'].rolling(50).mean().iloc[-1] if len(df) >= 50 else atr

        if adx > self.thresholds['adx_trend'] and rsi > self.thresholds['rsi_overbought']:
            self.regime = 'trending_up'
        elif adx > self.thresholds['adx_trend'] and rsi < self.thresholds['rsi_oversold']:
            self.regime = 'trending_down'
        elif atr > atr_mean * self.thresholds['atr_volatility']:
            self.regime = 'volatile'
        else:
            self.regime = 'ranging'
        return self.regime
