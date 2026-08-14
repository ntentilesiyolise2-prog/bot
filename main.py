#!/usr/bin/env python3
import os
import json
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

from data.fabric import DataFabric
from features.store import FeatureStore
from strategies.hierarchical_swarm import HierarchicalSwarm
from risk.engine import RiskEngine
from risk.circuit_breaker import CircuitBreaker
from risk.recovery_mode import RecoveryMode
from execution.core import ExecutionCore
from api.routes import router as api_router
from api.websocket import websocket_handler
from engine.core import TradingEngine
from engine.latency_arbitrage import LatencyArbitrage
from engine.market_maker import MarketMaker
from utils.telegram import TelegramBot
from utils.journal import TradeJournal
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger("main")

app = FastAPI(title="NEXUS INFINITUM", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

with open('config.json', 'r') as f:
    config = json.load(f)

# --- GLOBAL STATE ---
app.state.config = config
app.state.data_fabric = DataFabric()
app.state.feature_store = FeatureStore(app.state.data_fabric)
app.state.strategy_swarm = HierarchicalSwarm()
app.state.risk_engine = RiskEngine(config)
app.state.circuit_breaker = CircuitBreaker(
    max_daily_loss=config['risk']['max_daily_loss'],
    consecutive_loss_limit=config['risk']['max_consecutive_losses']
)
app.state.recovery_mode = RecoveryMode(app.state.circuit_breaker)
app.state.execution_core = ExecutionCore(config)
app.state.telegram = TelegramBot()
app.state.journal = TradeJournal()
app.state.engine = TradingEngine(app.state)
app.state.latency_arb = LatencyArbitrage(app.state)
app.state.market_maker = MarketMaker(app.state)
app.state.start_time = datetime.utcnow()

# --- API Routers ---
app.include_router(api_router)
app.add_api_websocket_route("/ws", websocket_handler)

# --- Serve Frontend ---
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

@app.on_event("startup")
async def startup():
    logger.info("🚀 Starting NEXUS INFINITUM v3.0...")
    await app.state.data_fabric.initialize()
    await app.state.execution_core.initialize()
    await app.state.engine.start()
    await app.state.market_maker.start()
    # Start latency arbitrage monitor
    asyncio.create_task(app.state.latency_arb.monitor())
    logger.info("✅ All systems ready. Engine is running.")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down...")
    await app.state.engine.stop()
    await app.state.execution_core.shutdown()
    await app.state.market_maker.stop()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
