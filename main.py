#!/usr/bin/env python3
import os
import json
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv

from data.fabric import DataFabric
from features.store import FeatureStore
from strategies.adaptive_swarm import AdaptiveSwarm
from risk.engine import RiskEngine
from risk.circuit_breaker import CircuitBreaker
from risk.recovery_mode import RecoveryMode
from execution.core import ExecutionCore
from api.routes import router as api_router
from api.websocket import websocket_handler
from api.voice_commands import router as voice_router
from api.learning_routes import router as learning_router
from api.comparison import router as comparison_router
from api.brain_visualisation import router as brain_router
from api.correlation import router as correlation_router
from api.import_export import router as import_export_router
from engine.core import TradingEngine
from engine.scheduler import schedule_nightly
from utils.telegram import TelegramBot
from utils.daily_briefing import DailyBriefing
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger("main")

app = FastAPI(title="NEXUS INFINITUM", version="3.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

# --- GLOBAL STATE ---
app.state.config = config
app.state.data_fabric = DataFabric()
app.state.feature_store = FeatureStore(app.state.data_fabric)
app.state.strategy_swarm = AdaptiveSwarm()
app.state.risk_engine = RiskEngine(config)
app.state.circuit_breaker = CircuitBreaker(
    max_daily_loss=config['risk']['max_daily_loss'],
    consecutive_loss_limit=config['risk']['max_consecutive_losses']
)
app.state.recovery_mode = RecoveryMode(app.state.circuit_breaker)
app.state.execution_core = ExecutionCore(config)
app.state.telegram = TelegramBot()
app.state.engine = TradingEngine(app.state)
app.state.daily_briefing = DailyBriefing(app.state)

# --- API Routers ---
app.include_router(api_router)
app.include_router(voice_router)
app.include_router(learning_router)
app.include_router(comparison_router)
app.include_router(brain_router)
app.include_router(correlation_router)
app.include_router(import_export_router)
app.add_api_websocket_route("/ws", websocket_handler)

# --- Serve Frontend ---
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

# --- Lifecycle Events ---
@app.on_event("startup")
async def startup():
    logger.info("🚀 Starting NEXUS INFINITUM v3.0...")
    await app.state.data_fabric.initialize()
    await app.state.execution_core.initialize()
    await app.state.engine.start()
    # Schedule nightly tasks
    schedule_nightly(app.state)
    logger.info("✅ All systems ready. Engine is running.")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down...")
    await app.state.engine.stop()
    await app.state.execution_core.shutdown()
    logger.info("👋 Goodbye.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
