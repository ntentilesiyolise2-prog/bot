from fastapi import APIRouter, WebSocket
import json
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            command = json.loads(data)
            action = command.get('action')
            symbol = command.get('symbol', 'BTCUSD')
            side = command.get('side')
            lot = command.get('lot', 0.01)

            if action == 'buy':
                order = {'symbol': symbol, 'side': 'BUY', 'lot': lot}
                result = await app.state.execution_core.execute_order(order)
                await websocket.send_text(json.dumps({"status": "executed", "order": result}))
            elif action == 'sell':
                order = {'symbol': symbol, 'side': 'SELL', 'lot': lot}
                result = await app.state.execution_core.execute_order(order)
                await websocket.send_text(json.dumps({"status": "executed", "order": result}))
            elif action == 'close_all':
                # Close all positions
                await app.state.execution_core.broker.flatten_all()
                await websocket.send_text(json.dumps({"status": "closed_all"}))
            else:
                await websocket.send_text(json.dumps({"status": "unknown_command"}))
    except Exception as e:
        logger.error(f"Voice WS error: {e}")
