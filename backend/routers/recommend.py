"""
recommend.py — /api/recommend router
Smart Triage: given KTAS level + specialty, rank hospitals by acceptance probability and ETA.
"""

import math
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal, List, Dict, Any
from services.data_engine import get_hospital_statuses, get_osint_alerts, HOSPITALS
from services.forecaster import adjust_status_index

router = APIRouter()

# Rough ETA from Bundang central (판교) in minutes — overridden by real GPS in production
BASE_ETA: Dict[str, int] = {
    "bsuh": 8,
    "cha":  6,
    "jss": 14,
}

SPECIALTY_MAP = {
    "trauma":     ["trauma"],
    "cardiac":    ["cardiac"],
    "neuro":      ["neuro"],
    "pediatric":  ["pediatric"],
    "obstetrics": ["obstetrics"],
    "internal":   ["internal"],
    "general":    [],  # any hospital
}


class TriageRequest(BaseModel):
    ktas: int                        # 1 = most critical, 5 = least
    specialty: str = "general"       # "trauma", "cardiac", "neuro", etc.
    location_lat: float = 37.3700   # default: 판교IC
    location_lng: float = 127.1050


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.post("/recommend")
def recommend(req: TriageRequest):
    alerts = get_osint_alerts()
    statuses = {h["id"]: h for h in get_hospital_statuses()}

    needed_specs = SPECIALTY_MAP.get(req.specialty, [])

    ranked: List[Dict[str, Any]] = []
    for h in HOSPITALS:
        hid = h["id"]
        status = statuses[hid]
        adjusted_si = adjust_status_index(status["status_index"], alerts)

        # Specialty check
        has_specialty = (not needed_specs) or any(s in status["available_specialties"] for s in needed_specs)

        # Distance-based ETA (approximation)
        dist_km = _haversine(req.location_lat, req.location_lng, h["lat"], h["lng"])
        eta_min = round(dist_km * 1.6 + 2)  # rough urban driving factor

        # KTAS urgency: for KTAS 1-2, penalise hospitals with low status_index heavily
        ktas_weight = 1.0
        if req.ktas <= 2 and adjusted_si < 40:
            ktas_weight = 0.5  # significantly penalise near-full hospitals for critical patients

        # Composite score: higher is better
        score = (adjusted_si * ktas_weight) - (eta_min * 1.5)
        if not has_specialty:
            score -= 40  # heavy penalty for missing specialty

        # Status label
        if adjusted_si >= 60:
            status_label = "green"
        elif adjusted_si >= 30:
            status_label = "amber"
        else:
            status_label = "red"

        ranked.append({
            "id": hid,
            "name": h["name"],
            "name_short": h["name_short"],
            "status_index": adjusted_si,
            "status": status_label,
            "available_beds": status["available_beds"],
            "eta_minutes": eta_min,
            "distance_km": round(dist_km, 1),
            "has_required_specialty": has_specialty,
            "available_specialties": status["available_specialties"],
            "score": round(score, 1),
            "recommendation_note": _note(adjusted_si, has_specialty, eta_min, req.ktas),
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    # Tag top recommendation
    if ranked:
        ranked[0]["is_top_pick"] = True

    return {
        "ktas": req.ktas,
        "specialty": req.specialty,
        "recommendations": ranked,
        "advisory": _advisory(req.ktas, ranked),
    }


def _note(si: int, has_spec: bool, eta: int, ktas: int) -> str:
    parts = []
    if not has_spec:
        parts.append("⚠️ 해당 전문의 부재")
    if si < 30:
        parts.append("🔴 수용 불가 위험")
    elif si < 60:
        parts.append("🟡 잔여 용량 주의")
    else:
        parts.append("🟢 수용 가능")
    if ktas <= 2 and eta > 10:
        parts.append(f"⏱ ETA {eta}분 — 우선 안정화 필요")
    return " · ".join(parts)


def _advisory(ktas: int, ranked: List[Dict]) -> str:
    if not ranked:
        return "추천 병원 없음"
    top = ranked[0]
    if top["status_index"] < 30:
        return "⚠️ 분당 내 모든 병원 포화 상태 — 용인/광주 권역 고려 요망"
    if ktas == 1:
        return f"🚨 KTAS 1 — 즉시 {top['name_short']} 이송 권고 (ETA {top['eta_minutes']}분)"
    return f"✅ {top['name_short']} 최우선 권고 — 수용지수 {top['status_index']}%"
