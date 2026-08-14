from fastapi import APIRouter, HTTPException, UploadFile, File, Header, Depends
from pydantic import BaseModel
from typing import Optional
import json
import csv
import io
from datetime import datetime

router = APIRouter()

# --- Security ---
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    app = router.app
    expected_key = app.state.config.get('security', {}).get('api_key', '')
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True

# --- Schemas ---
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
    writer = csv.DictWriter(output, fieldnames=trades[0].keys())
    writer.writeheader()
    for row in trades:
        writer.writerow(row)
    output.seek(0)
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=trades.csv"})

# ==================== OTHER ENDPOINTS (unchanged) ====================
# ... (keep all other endpoints from previous version: symbol search, vision, assistant, learning, comparison, recovery, briefing, correlation, brain, status, sos)
