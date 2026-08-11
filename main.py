#!/usr/bin/env python3
import os
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv

from data.fabric import DataFabric
from features.store import FeatureStore
from strategies.swarm import StrategySwarm
from risk.engine import RiskEngine
from execution.core import ExecutionCore
from api.routes import router as api_router
from api.websocket import websocket_handler
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger("main")

app = FastAPI(title="NEXUS INFINITUM", version="2.0.0")

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
    import json
    config = json.load(f)

# Global state
app.state.config = config
app.state.data_fabric = DataFabric()
app.state.feature_store = FeatureStore(app.state.data_fabric)
app.state.strategy_swarm = StrategySwarm()
app.state.risk_engine = RiskEngine(config)
app.state.execution_core = ExecutionCore(config)

# API routes
app.include_router(api_router)
app.add_api_websocket_route("/ws", websocket_handler)

# Serve frontend static files
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

@app.on_event("startup")
async def startup():
    logger.info("🚀 Starting NEXUS INFINITUM...")
    await app.state.execution_core.initialize()
    logger.info("✅ All systems ready.")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down...")
    await app.state.execution_core.shutdown()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
