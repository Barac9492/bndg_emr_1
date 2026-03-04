"""
alerts.py — /api/alerts router
"""

from fastapi import APIRouter, Query, Request
from services.data_engine import get_osint_alerts

router = APIRouter()


@router.get("/alerts")
async def alerts(request: Request, count: int = Query(default=8, ge=1, le=20)):
    http = request.app.state.http_client
    items = await get_osint_alerts(count=count, http_client=http)
    return {"alerts": items, "total": len(items)}
