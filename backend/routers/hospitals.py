"""
hospitals.py — /api/hospitals router
"""

from fastapi import APIRouter
from services.data_engine import get_hospital_statuses
from services.forecaster import adjust_status_index, forecast_demand_narrative
from services.data_engine import get_osint_alerts

router = APIRouter()


@router.get("/hospitals")
def hospitals():
    alerts = get_osint_alerts()
    statuses = get_hospital_statuses()
    for h in statuses:
        h["status_index"] = adjust_status_index(h["status_index"], alerts)
        # Re-evaluate status label after adjustment
        if h["status_index"] >= 60:
            h["status"] = "green"
        elif h["status_index"] >= 30:
            h["status"] = "amber"
        else:
            h["status"] = "red"
    return {
        "hospitals": statuses,
        "system_narrative": forecast_demand_narrative(alerts),
        "total_hospitals": len(statuses),
    }
