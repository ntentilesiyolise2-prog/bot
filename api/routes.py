from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import json
import base64

router = APIRouter()

# --- Schemas ---
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
    if result.get('status') not in ['rejected', 'failed']:
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
    return {"status": "updated"}

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
        from ai.vision.yolo_scanner import YOLOScanner
        scanner = YOLOScanner()
        image_bytes = await file.read()
        results = scanner.scan(image_bytes)
        return {"patterns": results}
    except ImportError:
        return {"error": "YOLO dependencies not installed."}
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
    except ImportError:
        return {"answer": "Assistant dependencies not installed."}
    except Exception as e:
        return {"answer": f"Error: {str(e)}"}

@router.post("/api/assistant/train_lstm")
async def train_lstm(symbol: str = "BTCUSD", timeframe: str = "D1"):
    app = router.app
    try:
        from ai.models.lstm_predictor import PricePredictor
        df = await app.state.data_fabric.get_candles(symbol, timeframe, limit=2000)
        if df.empty:
            return {"status": "failed", "error": "No data fetched."}
        predictor = PricePredictor()
        predictor.train(df, epochs=10)  # Quick training for demo
        return {"status": "success", "message": f"LSTM trained on {symbol}."}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
