"""
hospitals.py — /api/hospitals router
"""

from fastapi import APIRouter, Request
from services.data_engine import get_hospital_statuses, get_osint_alerts
from services.forecaster import adjust_status_index, forecast_demand_narrative

router = APIRouter()


@router.get("/hospitals")
async def hospitals(request: Request):
    http = request.app.state.http_client
    alerts = await get_osint_alerts(http_client=http)
    statuses = await get_hospital_statuses(http_client=http)

    for h in statuses:
        h["status_index"] = await adjust_status_index(h["status_index"], alerts, http_client=http)
        if h["status_index"] >= 60:
            h["status"] = "green"
        elif h["status_index"] >= 30:
            h["status"] = "amber"
        else:
            h["status"] = "red"

    return {
        "hospitals": statuses,
        "system_narrative": await forecast_demand_narrative(alerts, http_client=http),
        "total_hospitals": len(statuses),
    }
