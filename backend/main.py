"""
main.py — FastAPI application entry point for 분당 골든패스
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from routers import hospitals, alerts, recommend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage shared httpx client lifecycle."""
    settings = get_settings()
    
    try:
        app.state.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        
        api_sources = []
        if settings.use_egen:
            api_sources.append("E-Gen")
        if settings.use_kma:
            api_sources.append("KMA")
        if settings.use_traffic:
            api_sources.append("Traffic")
        
        mode = f"LIVE ({', '.join(api_sources)})" if api_sources else "MOCK (no API keys)"
        logger.info(f"[분당 골든패스] Starting in {mode} mode")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        if hasattr(app.state, 'http_client'):
            await app.state.http_client.aclose()
            logger.info("HTTP client closed")


app = FastAPI(
    title="분당 골든패스 API",
    description="OSINT 기반 응급의료 자원 최적화 플랫폼",
    version="1.2.0",
    lifespan=lifespan,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.vercel.app"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


app.include_router(hospitals.router, prefix="/api", tags=["Hospitals"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(recommend.router, prefix="/api", tags=["Triage"])


@app.get("/", response_model=Dict[str, Any])
def root() -> Dict[str, Any]:
    return {
        "service": "분당 골든패스", 
        "status": "running", 
        "version": "1.2.0"
    }


@app.get("/health", response_model=Dict[str, Any])
def health() -> Dict[str, Any]:
    settings = get_settings()
    return {
        "ok": True,
        "api_sources": {
            "egen": settings.use_egen,
            "kma": settings.use_kma,
            "traffic": settings.use_traffic,
        }
    }