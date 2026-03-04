"""
main.py — FastAPI application entry point for 분당 골든패스
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import hospitals, alerts, recommend

app = FastAPI(
    title="분당 골든패스 API",
    description="OSINT 기반 응급의료 자원 최적화 플랫폼",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                    "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hospitals.router, prefix="/api", tags=["Hospitals"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(recommend.router, prefix="/api", tags=["Triage"])


@app.get("/")
def root():
    return {"service": "분당 골든패스", "status": "running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"ok": True}
