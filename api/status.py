from fastapi import APIRouter
from datetime import datetime
import psutil
import os
from utils.journal import TradeJournal
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/api/status")
async def get_system_status():
    app = router.app
    journal = TradeJournal()
    trades = journal.get_trades(days=365)  # All time

    # Calculate win rate
    total_trades = len(trades)
    win_trades = [t for t in trades if t.get('pnl', 0) > 0]
    win_rate = (len(win_trades) / total_trades * 100) if total_trades > 0 else 0

    # Get active positions
    active_positions = len(app.state.execution_core.broker.positions) if hasattr(app.state.execution_core.broker, 'positions') else 0

    # Drawdown (simplified – from risk engine)
    drawdown = 0
    if hasattr(app.state.risk_engine, 'max_drawdown'):
        drawdown = app.state.risk_engine.max_drawdown

    # Uptime
    uptime_seconds = (datetime.utcnow() - app.state.start_time).total_seconds() if hasattr(app.state, 'start_time') else 0
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    # Broker status
    broker_status = "Connected" if app.state.execution_core.broker.connected else "Disconnected"

    # Data provider
    data_provider = "Yahoo Finance (active)"  # Could be more dynamic

    # Last signal
    last_signal = None
    if hasattr(app.state.scanner, 'last_results'):
        for sym, res in app.state.scanner.last_results.items():
            if res:
                last_signal = f"{sym}: {res.get('direction', 'N/A')} ({res.get('confluence', 0)}%)"
                break

    return {
        "uptime": f"{hours}h {minutes}m",
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "drawdown": round(drawdown, 2),
        "active_positions": active_positions,
        "last_signal": last_signal or "No signals yet",
        "broker_status": broker_status,
        "data_provider": data_provider,
        "engine_status": "Running" if app.state.engine.running else "Stopped"
    }
