from fastapi import APIRouter, HTTPException
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
    # Will be enhanced with live data from engine
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
    
    # --- Send Telegram Alert on successful trade ---
    if result.get('status') != 'rejected' and result.get('status') != 'failed':
        msg = (
            f"✅ <b>Trade Executed</b>\n"
            f"Symbol: {order['symbol']}\n"
            f"Side: {order['side']}\n"
            f"Lot: {order['lot']}\n"
            f"Price: {order.get('price', 'Market')}\n"
            f"ID: {result.get('id', 'N/A')}"
        )
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
    # Optional: reload config in app state
    app = router.app
    app.state.config = settings
    return {"status": "updated"}

@router.get("/api/account")
async def get_account():
    app = router.app
    # Pull from simulator or broker
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
