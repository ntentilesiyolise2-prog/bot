import pandas as pd
import numpy as np
from collections import deque

class LiquidityFractionStrategy:
    def __init__(self):
        self.name = "liquidity_fraction"
        self.performance = deque(maxlen=50)

    def get_signal(self, df):
        """
        Detects where retail stop-losses are clustered and sweeps them.
        Returns 'BUY' if sweeping below, 'SELL' if sweeping above.
        """
        if len(df) < 20:
            return "HOLD"

        # 1. Find recent swing highs and lows
        high_20 = df['High'].rolling(20).max()
        low_20 = df['Low'].rolling(20).min()
        last_high = high_20.iloc[-2]
        last_low = low_20.iloc[-2]
        current_close = df['Close'].iloc[-1]

        # 2. Calculate typical retail stop-loss clusters (above highs / below lows)
        stop_loss_above = last_high + (last_high - last_low) * 0.1
        stop_loss_below = last_low - (last_high - last_low) * 0.1

        # 3. Check for liquidity sweep setup
        # If price is approaching the low cluster, we expect a sweep down then reverse (BUY)
        # If price is approaching the high cluster, we expect a sweep up then reverse (SELL)
        
        atr = df['atr_14'].iloc[-1]
        price = current_close

        # Buy Setup: Price near lower liquidity zone and RSI oversold
        if price < stop_loss_below + atr and df['rsi_14'].iloc[-1] < 35:
            return "BUY"
        
        # Sell Setup: Price near upper liquidity zone and RSI overbought
        if price > stop_loss_above - atr and df['rsi_14'].iloc[-1] > 65:
            return "SELL"
        
        return "HOLD"

    def update_performance(self, pnl):
        self.performance.append(pnl)


# The main Adaptive Swarm now dominated by Liquidity Fraction
class AdaptiveSwarm:
    def __init__(self):
        # Primary engine: Liquidity Fraction (80% weight)
        self.primary = LiquidityFractionStrategy()
        # Backup strategies (20% weight combined)
        self.backups = []
        self.primary_weight = 0.8
        self.backup_weight = 0.2

    def get_votes(self, df):
        # Primary signal
        primary_signal = self.primary.get_signal(df)
        
        # Backup signals (simple momentum/trend as fallback)
        # Use MACD for backup
        if len(df) > 26:
            macd = df['macd'].iloc[-1]
            signal = df['macd_signal'].iloc[-1]
            backup_signal = "BUY" if macd > signal else "SELL" if macd < signal else "HOLD"
        else:
            backup_signal = "HOLD"

        # Weighted decision
        if primary_signal != "HOLD":
            final_dir = primary_signal
            confluence = 95.0  # HIGH CONFIDENCE
        else:
            final_dir = backup_signal
            confluence = 60.0  # Low confidence fallback

        return {
            'direction': final_dir,
            'confluence': round(confluence, 1),
            'votes': [primary_signal, backup_signal],
            'breakdown': {
                'buy': 80 if final_dir == "BUY" else 20,
                'sell': 80 if final_dir == "SELL" else 20,
                'hold': 20 if final_dir == "HOLD" else 60
            }
        }
