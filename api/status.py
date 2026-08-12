from fastapi import APIRouter
from datetime import datetime
import os
import psutil
from utils.journal import TradeJournal
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/api/status")
async def get_system_status():
    """
    Returns a comprehensive status report of the bot.
    Used by the hamburger menu "System Status" item.
    """
    app = router.app
    journal = TradeJournal()
    trades = journal.get_trades(days=365)  # All time

    # Win Rate
    total_trades = len(trades)
    win_trades = [t for t in trades if t.get('pnl', 0) > 0]
    win_rate = (len(win_trades) / total_trades * 100) if total_trades > 0 else 0

    # Active Positions
    active_positions = 0
    if hasattr(app.state.execution_core, 'broker'):
        broker = app.state.execution_core.broker
        active_positions = len(broker.positions) if hasattr(broker, 'positions') else 0

    # Drawdown (from risk engine)
    drawdown = 0
    if hasattr(app.state.risk_engine, 'max_drawdown'):
        drawdown = app.state.risk_engine.max_drawdown

    # Uptime
    uptime_seconds = 0
    if hasattr(app.state, 'start_time'):
        uptime_seconds = (datetime.utcnow() - app.state.start_time).total_seconds()
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    # Broker Status
    broker_status = "Connected" if app.state.execution_core.broker.connected else "Disconnected"

    # Data Provider (simplified)
    data_provider = "Yahoo Finance (active)"

    # Last Signal
    last_signal = "No signals yet"
    if hasattr(app.state.scanner, 'last_results'):
        for sym, res in app.state.scanner.last_results.items():
            if res:
                last_signal = f"{sym}: {res.get('direction', 'N/A')} ({res.get('confluence', 0)}%)"
                break

    # Engine Status
    engine_status = "Running" if app.state.engine.running else "Stopped"

    # System resources (optional)
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    memory_used = memory.used / (1024 ** 3)  # GB
    memory_total = memory.total / (1024 ** 3)  # GB

    return {
        "uptime": f"{hours}h {minutes}m",
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "drawdown": round(drawdown, 2),
        "active_positions": active_positions,
        "last_signal": last_signal,
        "broker_status": broker_status,
        "data_provider": data_provider,
        "engine_status": engine_status,
        "cpu_usage": round(cpu_percent, 1),
        "memory_used": round(memory_used, 2),
        "memory_total": round(memory_total, 2)
    }
