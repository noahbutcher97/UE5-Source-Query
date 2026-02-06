"""
UE5 Source Query - Asynchronous API Server (v2.1)
FastAPI implementation for low-latency, concurrent search.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Depends, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ue5_query.core.hybrid_query_relational import RelationalHybridEngine
from ue5_query.server.models import SearchRequest, SearchResponse, HealthStatus
from ue5_query.utils.logger import get_project_logger
from ue5_query.utils.config_manager import ConfigManager

logger = get_project_logger(__name__)

# --- Lifespan Management ---

class AppState:
    """Shared application state container"""
    def __init__(self):
        self.engine: Optional[RelationalHybridEngine] = None
        self.config: Optional[ConfigManager] = None
        self.start_time = time.time()

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events"""
    logger.info("Starting UE5 Source Query API...")
    
    # Initialize Engine
    root = Path(__file__).resolve().parent.parent.parent
    state.config = ConfigManager(root)
    state.engine = RelationalHybridEngine(root, state.config)
    
    try:
        await state.engine.initialize()
        logger.info("Search Engine initialized successfully.")
    except Exception as e:
        logger.error(f"Critical Failure during engine initialization: {e}")
        # We don't crash the server here to allow diagnostics via /health
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")
    if state.engine:
        await state.engine.close()

# --- API Configuration ---

app = FastAPI(
    title="UE5 Source Query API",
    description="Asynchronous search service for Unreal Engine 5 source code.",
    version="2.1.0",
    lifespan=lifespan
)

# Robustness: Add CORS for potential browser-based admin tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security ---

async def verify_api_key(x_api_key: str = Header(None)):
    """
    Simple API Key validation. 
    In production, this would check against a DB or Redis.
    For local robustness, it checks against an environment variable.
    """
    expected_key = os.getenv("UE5_QUERY_API_KEY")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return x_api_key

# --- Endpoints ---

@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(request: SearchRequest, _ = Security(verify_api_key)):
    """
    Perform a hybrid semantic/definition search.
    Routes to RelationalHybridEngine for non-blocking execution.
    """
    if not state.engine or not state.engine._is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search engine is still initializing or failed to start."
        )
    
    try:
        results = await state.engine.query(
            question=request.question,
            top_k=request.top_k,
            scope=request.scope,
            use_reranker=request.use_reranker
        )
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/health", response_model=HealthStatus, tags=["System"])
async def health_check():
    """
    Detailed system health report.
    Checks connectivity to SQLite and status of embeddings.
    """
    engine_ready = state.engine is not None and state.engine._is_ready
    db_ok = False
    
    if engine_ready:
        try:
            # Simple check to verify DB is responsive
            await state.engine.db.fetch_one("SELECT 1")
            db_ok = True
        except:
            db_ok = False

    return {
        "status": "online" if (engine_ready and db_ok) else "degraded",
        "database": db_ok,
        "embeddings": engine_ready,
        "gpu": os.environ.get("UE5_QUERY_HAS_GPU") == "1",
        "version": "2.1.0"
    }

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to docs"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    # Local-first configuration
    uvicorn.run(app, host="127.0.0.1", port=8000)
