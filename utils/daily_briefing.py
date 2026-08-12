from datetime import datetime
from utils.journal import TradeJournal
from utils.telegram import TelegramBot
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DailyBriefing:
    def __init__(self, app_state):
        self.app = app_state
        self.telegram = TelegramBot()
        self.journal = TradeJournal()

    async def generate(self):
        """
        Generate a daily performance report using real trades from the journal.
        Sends the report via Telegram.
        """
        # Get trades from the last 24 hours
        trades = self.journal.get_trades(days=1)
        
        if not trades:
            await self.telegram.send_message(
                f"📊 Daily Briefing - {datetime.now().strftime('%Y-%m-%d')}\nNo trades in the last 24 hours."
            )
            return

        total_pnl = sum(t['pnl'] for t in trades)
        win_trades = [t for t in trades if t['pnl'] > 0]
        loss_trades = [t for t in trades if t['pnl'] < 0]
        win_rate = len(win_trades) / len(trades) * 100 if trades else 0
        
        best_trade = max(trades, key=lambda x: x['pnl']) if trades else None
        worst_trade = min(trades, key=lambda x: x['pnl']) if trades else None

        # Build report
        report_lines = [
            f"📊 Daily Briefing - {datetime.now().strftime('%Y-%m-%d')}",
            f"Total Trades: {len(trades)}",
            f"Total PnL: ${total_pnl:.2f}",
            f"Win Rate: {win_rate:.1f}%",
            f"Wins: {len(win_trades)} | Losses: {len(loss_trades)}",
        ]
        
        if best_trade:
            report_lines.append(f"🏆 Best Trade: {best_trade['symbol']} +${best_trade['pnl']:.2f}")
        if worst_trade:
            report_lines.append(f"📉 Worst Trade: {worst_trade['symbol']} {worst_trade['pnl']:.2f}")
        
        report = "\n".join(report_lines)
        
        # Send via Telegram
        await self.telegram.send_message(report)
        logger.info("Daily briefing sent successfully.")
