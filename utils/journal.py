import json
import os
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)

class TradeJournal:
    def __init__(self, file_path="trades.json", max_active=500):
        self.file_path = file_path
        self.max_active = max_active
        self.trades = self._load()
        self.archive_enabled = True

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    trades = json.load(f)
                    # Ensure we don't load more than max_active
                    if len(trades) > self.max_active:
                        self._archive_old(trades)
                    return trades[-self.max_active:]
            except:
                return []
        return []

    def _archive_old(self, trades):
        archive_path = f"trades_archive_{datetime.utcnow().strftime('%Y%m%d')}.json"
        old_trades = trades[:-self.max_active]
        if os.path.exists(archive_path):
            with open(archive_path, 'r') as f:
                existing = json.load(f)
                old_trades = existing + old_trades
        with open(archive_path, 'w') as f:
            json.dump(old_trades, f, indent=4)
        logger.info(f"Archived {len(old_trades)} trades to {archive_path}")

    def _save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.trades, f, indent=4)

    def add_trade(self, trade):
        trade['timestamp'] = datetime.utcnow().isoformat()
        self.trades.append(trade)
        if len(self.trades) > self.max_active and self.archive_enabled:
            self._archive_old(self.trades)
            self.trades = self.trades[-self.max_active:]
        self._save()
        logger.info(f"📝 Trade saved: {trade.get('symbol')} {trade.get('side')}")

    def get_trades(self, source=None, days=30):
        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        result = []
        for t in self.trades:
            t_time = datetime.fromisoformat(t['timestamp']).timestamp()
            if t_time > cutoff:
                if source is None or t.get('source') == source:
                    result.append(t)
        return result
