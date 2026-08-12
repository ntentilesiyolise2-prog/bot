from fastapi import APIRouter
import pandas as pd
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/api/comparison")
async def get_comparison(user_id: str = "default"):
    # Simulate human trades from learning mode (would be stored)
    human_trades = [
        {'symbol': 'BTCUSD', 'side': 'BUY', 'entry': 68000, 'exit': 68100, 'pnl': 100},
        {'symbol': 'EURUSD', 'side': 'SELL', 'entry': 1.10, 'exit': 1.11, 'pnl': -100},
    ]
    # Simulate bot trades (from journal)
    bot_trades = [
        {'symbol': 'BTCUSD', 'side': 'BUY', 'entry': 68000, 'exit': 68200, 'pnl': 200},
        {'symbol': 'EURUSD', 'side': 'SELL', 'entry': 1.10, 'exit': 1.09, 'pnl': 100},
    ]
    human_df = pd.DataFrame(human_trades)
    bot_df = pd.DataFrame(bot_trades)
    comparison = {
        "human_win_rate": (human_df['pnl'] > 0).mean() * 100,
        "bot_win_rate": (bot_df['pnl'] > 0).mean() * 100,
        "human_total_pnl": human_df['pnl'].sum(),
        "bot_total_pnl": bot_df['pnl'].sum(),
        "human_avg_pnl": human_df['pnl'].mean(),
        "bot_avg_pnl": bot_df['pnl'].mean(),
        "difference": bot_df['pnl'].sum() - human_df['pnl'].sum(),
    }
    return comparison
