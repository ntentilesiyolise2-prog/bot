import json
import os
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)

class TradeJournal:
    def __init__(self, file_path="trades.json"):
        self.file_path = file_path
        self.trades = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.trades, f, indent=4)

    def add_trade(self, trade):
        trade['timestamp'] = datetime.utcnow().isoformat()
        self.trades.append(trade)
        self._save()
        logger.info(f"📝 Trade saved: {trade['symbol']} {trade['side']}")

    def get_trades(self, source=None, days=30):
        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        result = []
        for t in self.trades:
            t_time = datetime.fromisoformat(t['timestamp']).timestamp()
            if t_time > cutoff:
                if source is None or t.get('source') == source:
                    result.append(t)
        return result
