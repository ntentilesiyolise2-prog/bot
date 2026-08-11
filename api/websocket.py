from fastapi import WebSocket
import json
import asyncio
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for conn in self.active_connections:
            try:
                await conn.send_text(json.dumps(message))
            except:
                pass

manager = ConnectionManager()

async def websocket_handler(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get('action') == 'subscribe':
                    symbols = msg.get('symbols', [])
                    logger.info(f"Subscribed to {symbols}")
                    await websocket.send_text(json.dumps({"type": "subscribed", "symbols": symbols}))
            except:
                pass
    except:
        pass
    finally:
        manager.disconnect(websocket)
