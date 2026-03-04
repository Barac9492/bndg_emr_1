"""
main.py — FastAPI application entry point for 분당 골든패스
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import hospitals, alerts, recommend


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage shared httpx client lifecycle."""
    settings = get_settings()
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
    print(f"[분당 골든패스] Starting in {mode} mode")
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="분당 골든패스 API",
    description="OSINT 기반 응급의료 자원 최적화 플랫폼",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
        "https://*.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hospitals.router, prefix="/api", tags=["Hospitals"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(recommend.router, prefix="/api", tags=["Triage"])


@app.get("/")
def root():
    return {"service": "분당 골든패스", "status": "running", "version": "1.1.0"}


@app.get("/health")
def health():
    settings = get_settings()
    return {
        "ok": True,
        "api_sources": {
            "egen": settings.use_egen,
            "kma": settings.use_kma,
            "traffic": settings.use_traffic,
        },
    }
