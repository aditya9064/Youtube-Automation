"""
YouTube Automation Web App - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import json
import asyncio
from typing import List, Dict, Any
from datetime import datetime
import os
import sys

# Add parent directory to path for importing automation modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from database.models import init_db
from database.connection import get_database
from api.routes import pipeline, videos, analytics, config
from core.websocket_manager import WebSocketManager
from core.pipeline_manager import PipelineManager

# Initialize managers
websocket_manager = WebSocketManager()
pipeline_manager = PipelineManager(websocket_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await pipeline_manager.start()
    yield
    # Shutdown
    await pipeline_manager.stop()

# Create FastAPI application
app = FastAPI(
    title="YouTube Automation Pipeline",
    description="AI-powered video generation and YouTube upload automation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(pipeline.router, prefix="/api/v1/pipeline", tags=["pipeline"])
app.include_router(videos.router, prefix="/api/v1/videos", tags=["videos"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(config.router, prefix="/api/v1/config", tags=["config"])

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "subscribe":
                await websocket_manager.subscribe(websocket, message.get("channel", "default"))
            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "YouTube Automation Pipeline API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "websocket_url": "/ws"
    }

# Serve static files (for production)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )