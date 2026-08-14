from fastapi import APIRouter, HTTPException, UploadFile, File, Header, Depends, Response
from pydantic import BaseModel
from typing import Optional
import json
import csv
import io
from datetime import datetime

router = APIRouter()

# ==================== SECURITY ====================
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """
    Simple API key verification. If a key is set in config.json, it must be provided.
    """
    app = router.app
    expected_key = app.state.config.get('security', {}).get('api_key', '')
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True

# ==================== SCHEMAS ====================
class TradeRequest(BaseModel):
    symbol: str
    side: str
    lot: float
    price: Optional[float] = None

class QueryRequest(BaseModel):
    question: str

# ==================== CORE ENDPOINTS ====================
@router.get("/api/quotes", dependencies=[Depends(verify_api_key)])
async def get_quotes():
    """Placeholder – real quotes come via WebSocket."""
    return {"symbols": []}

@router.get("/api/candles", dependencies=[Depends(verify_api_key)])
async def get_candles(symbol: str, timeframe: str, limit: int = 500):
    app = router.app
    df = await app.state.data_fabric.get_candles(symbol, timeframe, limit)
    return df.to_dict(orient='records')

@router.post("/api/execute_trade", dependencies=[Depends(verify_api_key)])
async def execute_trade(trade: TradeRequest):
    app = router.app
    order = trade.dict()
    result = await app.state.execution_core.execute_order(order)
    if result.get('status') == 'executed':
        msg = f"✅ Trade Executed\nSymbol: {order['symbol']}\nSide: {order['side']}\nLot: {order['lot']}"
        await app.state.telegram.send_message(msg)
    return result

@router.get("/api/settings", dependencies=[Depends(verify_api_key)])
async def get_settings():
    with open('config.json', 'r') as f:
        return json.load(f)

@router.post("/api/settings", dependencies=[Depends(verify_api_key)])
async def update_settings(settings: dict):
    with open('config.json', 'w') as f:
        json.dump(settings, f, indent=4)
    app = router.app
    app.state.config = settings
    app.state.engine.auto_trade_enabled = settings.get('ai', {}).get('auto_trade', True)
    return {"status": "updated"}

@router.post("/api/auto_trade/toggle", dependencies=[Depends(verify_api_key)])
async def toggle_auto_trade(enable: bool):
    app = router.app
    app.state.config['ai']['auto_trade'] = enable
    with open('config.json', 'w') as f:
        json.dump(app.state.config, f, indent=4)
    return {"status": "ok", "auto_trade": enable}

@router.get("/api/account", dependencies=[Depends(verify_api_key)])
async def get_account():
    app = router.app
    broker = app.state.execution_core.broker
    return {
        "balance": getattr(broker, 'balance', 10000.0),
        "equity": getattr(broker, 'balance', 10000.0),
        "free_margin": getattr(broker, 'balance', 10000.0),
    }

@router.get("/api/positions", dependencies=[Depends(verify_api_key)])
async def get_positions():
    app = router.app
    broker = app.state.execution_core.broker
    return {"positions": getattr(broker, 'positions', [])}

# ==================== SYMBOL MANAGEMENT ====================
from data.symbol_info import SymbolInfo

@router.get("/api/symbols/search", dependencies=[Depends(verify_api_key)])
async def search_symbols(q: str):
    symbol_info = SymbolInfo()
    results = symbol_info.search_symbols(q)
    return {"results": results}

@router.post("/api/symbols/add", dependencies=[Depends(verify_api_key)])
async def add_symbol(symbol: str):
    app = router.app
    success = await app.state.engine.add_symbol(symbol)
    if success:
        if symbol not in app.state.config['symbols']:
            app.state.config['symbols'].append(symbol)
            with open('config.json', 'w') as f:
                json.dump(app.state.config, f, indent=4)
        return {"status": "added", "symbol": symbol}
    return {"status": "failed", "symbol": symbol}

@router.delete("/api/symbols/remove", dependencies=[Depends(verify_api_key)])
async def remove_symbol(symbol: str):
    app = router.app
    success = await app.state.engine.remove_symbol(symbol)
    if success:
        if symbol in app.state.config['symbols']:
            app.state.config['symbols'].remove(symbol)
            with open('config.json', 'w') as f:
                json.dump(app.state.config, f, indent=4)
        return {"status": "removed", "symbol": symbol}
    return {"status": "failed", "symbol": symbol}

# ==================== PENDING ORDERS ====================
@router.get("/api/pending_orders", dependencies=[Depends(verify_api_key)])
async def get_pending_orders():
    app = router.app
    return {"pending": app.state.execution_core.pending_orders}

# ==================== CSV EXPORT ====================
@router.get("/api/history/export", dependencies=[Depends(verify_api_key)])
async def export_history():
    app = router.app
    journal = app.state.journal
    trades = journal.get_trades(days=365)
    if not trades:
        raise HTTPException(status_code=404, detail="No trades found")
    output = io.StringIO()
    if trades:
        writer = csv.DictWriter(output, fieldnames=trades[0].keys())
        writer.writeheader()
        for row in trades:
            writer.writerow(row)
    output.seek(0)
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=trades.csv"})

# ==================== VISION (GEMINI / OPENROUTER) ====================
@router.post("/api/analyze_chart", dependencies=[Depends(verify_api_key)])
async def analyze_chart(file: UploadFile = File(...)):
    app = router.app
    try:
        image_bytes = await file.read()
        result = await app.state.scanner.scan_image(image_bytes, "BTCUSD", "M15")
        return {"patterns": result}
    except Exception as e:
        return {"error": str(e)}

# ==================== ASSISTANT (RAG + GROQ) ====================
@router.post("/api/assistant/query", dependencies=[Depends(verify_api_key)])
async def assistant_query(query: QueryRequest):
    app = router.app
    try:
        from ai.assistant.rag_engine import RAGAssistant
        assistant = RAGAssistant()
        await assistant.initialize()
        answer = await assistant.query(query.question)
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Error: {str(e)}"}

# ==================== LEARNING MODE ====================
from ai.learning.lesson_db import LESSONS, LessonManager

@router.get("/api/learning/lessons", dependencies=[Depends(verify_api_key)])
async def get_lessons(level: str = "beginner"):
    return LESSONS.get(level, [])

@router.get("/api/learning/next", dependencies=[Depends(verify_api_key)])
async def get_next_lesson(level: str, current_id: int):
    manager = LessonManager()
    next_lesson = manager.get_next_lesson(level, current_id)
    if next_lesson:
        return next_lesson
    return {"message": "No more lessons"}

@router.post("/api/learning/complete", dependencies=[Depends(verify_api_key)])
async def mark_complete(user_id: str, lesson_id: int):
    manager = LessonManager()
    progress = manager.mark_complete(user_id, lesson_id)
    return progress

# ==================== COMPARISON (BOT vs HUMAN) ====================
@router.get("/api/comparison", dependencies=[Depends(verify_api_key)])
async def get_comparison():
    from utils.journal import TradeJournal
    journal = TradeJournal()
    trades = journal.get_trades(days=30)
    human_trades = [t for t in trades if t.get('source') == 'human']
    bot_trades = [t for t in trades if t.get('source') == 'bot']
    def calc(trades_list):
        if not trades_list:
            return {"win_rate": 0, "total_pnl": 0, "avg_pnl": 0, "count": 0}
        import pandas as pd
        df = pd.DataFrame(trades_list)
        win_rate = (df['pnl'] > 0).mean() * 100
        total_pnl = df['pnl'].sum()
        avg_pnl = df['pnl'].mean()
        return {"win_rate": round(win_rate,1), "total_pnl": round(total_pnl,2), "avg_pnl": round(avg_pnl,2), "count": len(df)}
    human = calc(human_trades)
    bot = calc(bot_trades)
    return {
        "human_win_rate": human["win_rate"],
        "bot_win_rate": bot["win_rate"],
        "human_total_pnl": human["total_pnl"],
        "bot_total_pnl": bot["total_pnl"],
        "human_avg_pnl": human["avg_pnl"],
        "bot_avg_pnl": bot["avg_pnl"],
        "human_count": human["count"],
        "bot_count": bot["count"],
        "difference": round(bot["total_pnl"] - human["total_pnl"], 2)
    }

# ==================== RECOVERY MODE ====================
@router.get("/api/recovery/status", dependencies=[Depends(verify_api_key)])
async def get_recovery_status():
    app = router.app
    return {"recovery_active": app.state.recovery_mode.recovery_active}

@router.post("/api/recovery/reset", dependencies=[Depends(verify_api_key)])
async def reset_recovery():
    app = router.app
    app.state.recovery_mode.recovery_active = False
    app.state.recovery_mode.recovery_step = 0
    app.state.circuit_breaker.tripped = False
    return {"status": "recovery_reset"}

# ==================== DAILY BRIEFING ====================
@router.post("/api/briefing/send", dependencies=[Depends(verify_api_key)])
async def send_briefing():
    app = router.app
    await app.state.daily_briefing.generate()
    return {"status": "briefing_sent"}

# ==================== CORRELATION MATRIX ====================
@router.get("/api/correlation", dependencies=[Depends(verify_api_key)])
async def get_correlation():
    app = router.app
    symbols = app.state.config.get('symbols', ['BTCUSD', 'EURUSD', 'GOLD'])
    data = {}
    for sym in symbols:
        df = await app.state.data_fabric.get_candles(sym, "D1", limit=100)
        if not df.empty:
            data[sym] = df['Close'].pct_change()
    import pandas as pd
    df = pd.DataFrame(data)
    corr = df.corr().round(2)
    return corr.to_dict()

# ==================== BRAIN VISUALISATION ====================
@router.get("/api/brain/feature_importance", dependencies=[Depends(verify_api_key)])
async def get_feature_importance():
    from ai.models.xgboost_model import XGBoostModel
    model = XGBoostModel()
    importance = model.get_feature_importance()
    return {"features": importance}

# ==================== SYSTEM STATUS ====================
@router.get("/api/status", dependencies=[Depends(verify_api_key)])
async def get_system_status():
    app = router.app
    from utils.journal import TradeJournal
    import psutil
    journal = TradeJournal()
    trades = journal.get_trades(days=365)
    total_trades = len(trades)
    win_trades = [t for t in trades if t.get('pnl', 0) > 0]
    win_rate = (len(win_trades) / total_trades * 100) if total_trades > 0 else 0
    active_positions = len(app.state.execution_core.broker.positions) if hasattr(app.state.execution_core.broker, 'positions') else 0
    drawdown = app.state.risk_engine.max_drawdown if hasattr(app.state.risk_engine, 'max_drawdown') else 0
    uptime_seconds = (datetime.utcnow() - app.state.start_time).total_seconds() if hasattr(app.state, 'start_time') else 0
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    broker_status = "Connected" if app.state.execution_core.broker.connected else "Disconnected"
    engine_status = "Running" if app.state.engine.running else "Stopped"
    last_signal = "No signals yet"
    if hasattr(app.state.scanner, 'last_results'):
        for sym, res in app.state.scanner.last_results.items():
            if res:
                last_signal = f"{sym}: {res.get('direction', 'N/A')} ({res.get('confluence', 0)}%)"
                break
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    return {
        "uptime": f"{hours}h {minutes}m",
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "drawdown": round(drawdown, 2),
        "active_positions": active_positions,
        "last_signal": last_signal,
        "broker_status": broker_status,
        "engine_status": engine_status,
        "cpu_usage": round(cpu, 1),
        "memory_used": round(mem.used / (1024**3), 2),
        "memory_total": round(mem.total / (1024**3), 2)
    }

# ==================== SOS PANIC BUTTON ====================
import asyncio

@router.post("/api/sos", dependencies=[Depends(verify_api_key)])
async def sos_panic():
    app = router.app
    # Flatten all positions
    await app.state.execution_core.flatten_all()
    # Cancel pending orders
    app.state.execution_core.pending_orders.clear()
    # Pause auto‑trade for 1 hour
    app.state.engine.auto_trade_enabled = False
    # Notify via Telegram
    await app.state.telegram.send_message("🚨 SOS PANIC ACTIVATED. All positions flattened. Engine paused for 1 hour.")
    # Schedule auto‑restart
    asyncio.create_task(_auto_restart_engine(app.state))
    return {"status": "panic_activated", "engine_paused": True}

async def _auto_restart_engine(app_state):
    await asyncio.sleep(3600)  # 1 hour
    app_state.engine.auto_trade_enabled = True
    await app_state.telegram.send_message("✅ Engine auto‑restarted after SOS panic.")
    logger.info("Engine auto‑restarted after panic.")
