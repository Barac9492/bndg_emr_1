"""
alerts.py — /api/alerts router
"""

from fastapi import APIRouter, Query
from services.data_engine import get_osint_alerts

router = APIRouter()


@router.get("/alerts")
def alerts(count: int = Query(default=8, ge=1, le=20)):
    items = get_osint_alerts(count=count)
    return {"alerts": items, "total": len(items)}
