"""
Talking BI — FastAPI Backend
Agentic Voice-Enabled Business Intelligence
"""
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import settings
from core.database import init_db
from core.redis_client import init_redis
from core.vector_client import get_chroma_client
from api.routes import router as api_router
from api.websocket_handler import WebSocketManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Single global ws_manager — attached to app.state so routes can reach it
ws_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("🚀 Starting Talking BI backend...")
    await init_db()
    await init_redis()
    # Initialize Vector Memory
    get_chroma_client()
    # FIX #8: attach ws_manager to app.state so upload route can register files
    app.state.ws_manager = ws_manager
    logger.info("✅ Database, Redis, and WebSocket manager ready")
    yield
    logger.info("👋 Shutting down Talking BI backend...")


app = FastAPI(
    title="Talking BI API",
    description="Agentic Voice-Enabled Business Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Main WebSocket endpoint — real-time voice + agent communication."""
    await ws_manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await ws_manager.handle_message(websocket, session_id, message)
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)
        logger.info(f"Session {session_id} disconnected cleanly")
    except json.JSONDecodeError as e:
        logger.warning(f"Bad JSON from session {session_id}: {e}")
        ws_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
        ws_manager.disconnect(session_id)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Talking BI", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
