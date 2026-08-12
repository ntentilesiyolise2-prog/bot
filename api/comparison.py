from fastapi import APIRouter
import pandas as pd
from utils.journal import TradeJournal
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/api/comparison")
async def get_comparison(user_id: str = "default"):
    """
    Compare bot vs human performance using real trade data.
    Fetches trades from the persistent journal (trades.json).
    """
    journal = TradeJournal()
    trades = journal.get_trades(days=30)  # Last 30 days

    # Split into human and bot trades
    human_trades = [t for t in trades if t.get('source') == 'human']
    bot_trades = [t for t in trades if t.get('source') == 'bot']

    def calc_stats(trades_list):
        if not trades_list:
            return {
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl": 0,
                "count": 0,
                "best_trade": None,
                "worst_trade": None
            }
        df = pd.DataFrame(trades_list)
        win_rate = (df['pnl'] > 0).mean() * 100
        total_pnl = df['pnl'].sum()
        avg_pnl = df['pnl'].mean()
        best_idx = df['pnl'].idxmax() if len(df) > 0 else None
        worst_idx = df['pnl'].idxmin() if len(df) > 0 else None
        best_trade = df.iloc[best_idx].to_dict() if best_idx is not None else None
        worst_trade = df.iloc[worst_idx].to_dict() if worst_idx is not None else None
        return {
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "count": len(df),
            "best_trade": best_trade,
            "worst_trade": worst_trade
        }

    human_stats = calc_stats(human_trades)
    bot_stats = calc_stats(bot_trades)

    return {
        "human_win_rate": human_stats["win_rate"],
        "bot_win_rate": bot_stats["win_rate"],
        "human_total_pnl": human_stats["total_pnl"],
        "bot_total_pnl": bot_stats["total_pnl"],
        "human_avg_pnl": human_stats["avg_pnl"],
        "bot_avg_pnl": bot_stats["avg_pnl"],
        "human_count": human_stats["count"],
        "bot_count": bot_stats["count"],
        "human_best": human_stats["best_trade"],
        "bot_best": bot_stats["best_trade"],
        "human_worst": human_stats["worst_trade"],
        "bot_worst": bot_stats["worst_trade"],
        "difference": round(bot_stats["total_pnl"] - human_stats["total_pnl"], 2),
    }
