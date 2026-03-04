"""
data_engine.py
Simulates real-time hospital status and OSINT alert data for the 분당 골든패스 MVP.
In production, the hospital data would come from the E-Gen (응급의료포털) API.
"""

import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# Static hospital registry
# ---------------------------------------------------------------------------

HOSPITALS: List[Dict[str, Any]] = [
    {
        "id": "bsuh",
        "name": "분당서울대학교병원",
        "name_short": "서울대병원",
        "lat": 37.3520,
        "lng": 127.1235,
        "address": "경기도 성남시 분당구 구미로173번길 82",
        "phone": "031-787-7575",
        "specialties": ["trauma", "cardiac", "neuro", "pediatric"],
        "total_beds": 40,
        "equipment": ["CT", "MRI", "ECMO", "Cath-Lab"],
        "level": "권역응급의료센터",
        "base_load": 0.78,   # chronically busy flagship
    },
    {
        "id": "cha",
        "name": "분당차병원",
        "name_short": "차병원",
        "lat": 37.3406,
        "lng": 127.1218,
        "address": "경기도 성남시 분당구 야탑로59",
        "phone": "031-780-5000",
        "specialties": ["cardiac", "trauma", "obstetrics"],
        "total_beds": 28,
        "equipment": ["CT", "MRI", "Cath-Lab"],
        "level": "지역응급의료센터",
        "base_load": 0.65,
    },
    {
        "id": "jss",
        "name": "제생병원",
        "name_short": "제생병원",
        "lat": 37.4191,
        "lng": 127.1270,
        "address": "경기도 성남시 수정구 수정로 171",
        "phone": "031-750-1000",
        "specialties": ["trauma", "internal"],
        "total_beds": 18,
        "equipment": ["CT", "X-Ray"],
        "level": "지역응급의료기관",
        "base_load": 0.50,
    },
    {
        "id": "ysei",
        "name": "용인세브란스병원",
        "name_short": "용인세브란스",
        "lat": 37.2810,
        "lng": 127.1719,
        "address": "경기도 용인시 처인구 명지로 55",
        "phone": "031-331-8000",
        "specialties": ["trauma", "cardiac", "neuro", "obstetrics"],
        "total_beds": 35,
        "equipment": ["CT", "MRI", "Cath-Lab", "ECMO"],
        "level": "지역응급의료센터",
        "base_load": 0.42,   # further out — tends to have space
    },
    {
        "id": "snmc",
        "name": "성남시의료원",
        "name_short": "성남시의료원",
        "lat": 37.4432,
        "lng": 127.1491,
        "address": "경기도 성남시 중원구 둔촌대로 180",
        "phone": "031-738-7000",
        "specialties": ["internal", "trauma", "pediatric"],
        "total_beds": 22,
        "equipment": ["CT", "X-Ray", "MRI"],
        "level": "지역응급의료센터",
        "base_load": 0.38,   # public hospital with good surge capacity
    },
    {
        "id": "kcha",
        "name": "강남차병원",
        "name_short": "강남차병원",
        "lat": 37.5059,
        "lng": 127.0236,
        "address": "서울특별시 강남구 논현로 566",
        "phone": "02-3468-3000",
        "specialties": ["cardiac", "neuro", "obstetrics"],
        "total_beds": 30,
        "equipment": ["CT", "MRI", "Cath-Lab"],
        "level": "지역응급의료센터",
        "base_load": 0.55,
    },
]

# ---------------------------------------------------------------------------
# OSINT alert pool (simulated)
# ---------------------------------------------------------------------------

OSINT_POOL = [
    {"type": "traffic", "severity": "high",   "msg": "판교IC 5중 추돌사고 — 중상자 3명 추정"},
    {"type": "traffic", "severity": "medium", "msg": "분당수서도 상행 정체 — 구급차 소요 +8분"},
    {"type": "sns",     "severity": "high",   "msg": "맘카페 제보: 야탑역 근처 심정지 환자 발생"},
    {"type": "sns",     "severity": "low",    "msg": "트위터: 분당선 고장으로 승객 혼잡"},
    {"type": "weather", "severity": "medium", "msg": "기상청: 낙뢰 동반 폭우 예보 — 외상 수요 증가 예상"},
    {"type": "event",   "severity": "low",    "msg": "성남시청 마라톤 대회 (참가자 2,000명)"},
    {"type": "traffic", "severity": "high",   "msg": "정자교 역주행 사고 — 복수 부상자"},
    {"type": "sns",     "severity": "medium", "msg": "네이버 카페: 서현역 쓰러짐 목격담"},
    {"type": "weather", "severity": "low",    "msg": "기상청: 영하 5도 빙판길 예보"},
    {"type": "event",   "severity": "medium", "msg": "판교 테크노밸리 불꽃 행사 — 20,000명 예상"},
]

# ---------------------------------------------------------------------------
# Realistic simulation with time-of-day weighting
# ---------------------------------------------------------------------------

def _time_pressure() -> float:
    """Returns a multiplier (0.6–1.4) based on hour of day."""
    hour = datetime.now().hour
    if 8 <= hour <= 10 or 18 <= hour <= 21:   # peak
        return 1.35
    elif 0 <= hour <= 5:                        # quiet night
        return 0.65
    else:
        return 1.0


def _seed_from_time(salt: int = 0) -> int:
    """Returns a seed that changes every 30s for deterministic but evolving data."""
    t = datetime.now()
    return (t.year * 10000 + t.month * 100 + t.day) * 10000 + (t.hour * 60 + t.minute) * 2 + (t.second // 30) + salt


def get_hospital_statuses() -> List[Dict[str, Any]]:
    tod_pressure = _time_pressure()  # 0.65 – 1.35
    results = []

    for i, h in enumerate(HOSPITALS):
        rng = random.Random(_seed_from_time(salt=i * 17))

        # Each hospital has its own baseline load (encoded in static data).
        # Time-of-day pressure only shifts occupancy by ±20%, not multiplies wholesale.
        base_load: float = h.get("base_load", 0.60)
        tod_delta = (tod_pressure - 1.0) * 0.20   # maps 0.65–1.35 → -0.07 to +0.07
        noise = rng.uniform(-0.08, 0.08)
        occupancy = max(0.05, min(0.97, base_load + tod_delta + noise))
        available_beds = max(0, round(h["total_beds"] * (1 - occupancy)))

        # Status Index: 30-min acceptance probability
        status_index = round(max(3, min(98, (1 - occupancy) * 100)))

        # Trend
        prev_rng = random.Random(_seed_from_time(salt=i * 17) - 1)
        prev_noise = prev_rng.uniform(-0.08, 0.08)
        prev_occ = max(0.05, min(0.97, base_load + tod_delta + prev_noise))
        trend = "improving" if occupancy < prev_occ - 0.02 else "worsening" if occupancy > prev_occ + 0.02 else "stable"

        # Status label
        if status_index >= 60:
            status = "green"
        elif status_index >= 30:
            status = "amber"
        else:
            status = "red"

        # On-call specialties (randomly 1–2 offline)
        all_specs = h["specialties"][:]
        offline_count = rng.randint(0, min(1, len(all_specs) - 1))
        offline_specs = rng.sample(all_specs, offline_count)
        available_specs = [s for s in all_specs if s not in offline_specs]

        results.append({
            **h,
            "available_beds": available_beds,
            "occupancy_pct": round(occupancy * 100, 1),
            "status_index": status_index,
            "status": status,
            "trend": trend,
            "available_specialties": available_specs,
            "offline_specialties": offline_specs,
            "last_updated": datetime.now().isoformat(),
        })

    return results


def get_osint_alerts(count: int = 8) -> List[Dict[str, Any]]:
    rng = random.Random(_seed_from_time(salt=999))
    chosen = rng.choices(OSINT_POOL, k=count)
    alerts = []
    now = datetime.now()
    for i, item in enumerate(chosen):
        ts = now - timedelta(minutes=rng.randint(1, 45))
        alerts.append({
            "id": f"alert-{_seed_from_time()}-{i}",
            "type": item["type"],
            "severity": item["severity"],
            "message": item["msg"],
            "timestamp": ts.isoformat(),
            "minutes_ago": round((now - ts).total_seconds() / 60),
        })
    # Sort newest first
    alerts.sort(key=lambda x: x["timestamp"], reverse=True)
    return alerts
