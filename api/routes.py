from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import json

router = APIRouter()

class TradeRequest(BaseModel):
    symbol: str
    side: str
    lot: float
    price: Optional[float] = None

class QueryRequest(BaseModel):
    question: str

# --- Core Routes ---
@router.get("/api/quotes")
async def get_quotes():
    return {"symbols": []}

@router.get("/api/candles")
async def get_candles(symbol: str, timeframe: str, limit: int = 500):
    app = router.app
    df = await app.state.data_fabric.get_candles(symbol, timeframe, limit)
    return df.to_dict(orient='records')

@router.post("/api/execute_trade")
async def execute_trade(trade: TradeRequest):
    app = router.app
    order = trade.dict()
    result = await app.state.execution_core.execute_order(order)
    if result.get('status') == 'executed':
        msg = f"✅ Trade Executed\nSymbol: {order['symbol']}\nSide: {order['side']}\nLot: {order['lot']}"
        await app.state.telegram.send_message(msg)
    return result

@router.get("/api/settings")
async def get_settings():
    with open('config.json', 'r') as f:
        return json.load(f)

@router.post("/api/settings")
async def update_settings(settings: dict):
    with open('config.json', 'w') as f:
        json.dump(settings, f, indent=4)
    app = router.app
    app.state.config = settings
    # Reinit auto‑trade state
    app.state.engine.auto_trade_enabled = settings.get('ai', {}).get('auto_trade', True)
    return {"status": "updated"}

@router.post("/api/auto_trade/toggle")
async def toggle_auto_trade(enable: bool):
    app = router.app
    app.state.config['ai']['auto_trade'] = enable
    with open('config.json', 'w') as f:
        json.dump(app.state.config, f, indent=4)
    return {"status": "ok", "auto_trade": enable}

@router.get("/api/account")
async def get_account():
    app = router.app
    broker = app.state.execution_core.broker
    return {
        "balance": getattr(broker, 'balance', 10000.0),
        "equity": getattr(broker, 'balance', 10000.0),
        "free_margin": getattr(broker, 'balance', 10000.0),
    }

@router.get("/api/positions")
async def get_positions():
    app = router.app
    broker = app.state.execution_core.broker
    return {"positions": getattr(broker, 'positions', [])}

# --- Advanced Vision & AI Routes ---
@router.post("/api/analyze_chart")
async def analyze_chart(file: UploadFile = File(...)):
    app = router.app
    try:
        from ai.vision.openrouter_scanner import OpenRouterVisionScanner
        scanner = OpenRouterVisionScanner()
        image_bytes = await file.read()
        results = scanner.scan(image_bytes)
        return {"patterns": results}
    except Exception as e:
        return {"error": str(e)}

@router.post("/api/assistant/query")
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

# --- Symbol Management ---
from data.symbol_info import SymbolInfo

@router.get("/api/symbols/search")
async def search_symbols(q: str):
    symbol_info = SymbolInfo()
    results = symbol_info.search_symbols(q)
    return {"results": results}

@router.post("/api/symbols/add")
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

@router.delete("/api/symbols/remove")
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

# --- Recovery Mode ---
@router.get("/api/recovery/status")
async def get_recovery_status():
    app = router.app
    return {"recovery_active": app.state.recovery_mode.recovery_active}

@router.post("/api/recovery/reset")
async def reset_recovery():
    app = router.app
    app.state.recovery_mode.recovery_active = False
    app.state.recovery_mode.recovery_step = 0
    app.state.circuit_breaker.tripped = False
    return {"status": "recovery_reset"}

# --- Daily Briefing ---
@router.post("/api/briefing/send")
async def send_briefing():
    app = router.app
    await app.state.daily_briefing.generate()
    return {"status": "briefing_sent"}
