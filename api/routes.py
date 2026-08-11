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
    # Reinitialize auto‑trade state
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
