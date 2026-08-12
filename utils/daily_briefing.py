from datetime import datetime
import json
from utils.logger import setup_logger
from utils.telegram import TelegramBot

logger = setup_logger(__name__)

class DailyBriefing:
    def __init__(self, app_state):
        self.app = app_state
        self.telegram = TelegramBot()

    async def generate(self):
        # Fetch yesterday's trades
        # For now, simulate
        trades = [
            {'symbol': 'BTCUSD', 'pnl': 100},
            {'symbol': 'EURUSD', 'pnl': -20},
        ]
        total_pnl = sum(t['pnl'] for t in trades)
        win_trades = [t for t in trades if t['pnl'] > 0]
        loss_trades = [t for t in trades if t['pnl'] < 0]
        win_rate = len(win_trades) / len(trades) * 100 if trades else 0
        best = max(trades, key=lambda x: x['pnl']) if trades else None
        worst = min(trades, key=lambda x: x['pnl']) if trades else None

        report = f"""📊 Daily Briefing - {datetime.now().strftime('%Y-%m-%d')}
Total PnL: ${total_pnl:.2f}
Win Rate: {win_rate:.1f}%
Best Trade: {best['symbol']} +${best['pnl']:.2f} if best else 'N/A'
Worst Trade: {worst['symbol']} {worst['pnl']:.2f} if worst else 'N/A'
"""
        await self.telegram.send_message(report)
        logger.info("Daily briefing sent.")
