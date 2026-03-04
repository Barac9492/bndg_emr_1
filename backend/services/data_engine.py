"""
data_engine.py
Hospital status and OSINT alert data for 분당 골든패스.
Uses real APIs (E-Gen, Traffic) when keys are configured, falls back to mock data.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from services.api_clients.egen import EGenClient
from services.api_clients.traffic import TrafficClient

logger = logging.getLogger(__name__)

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
        "base_load": 0.78,
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
        "base_load": 0.42,
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
        "base_load": 0.38,
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
# OSINT alert pool (mock fallback)
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
# Time-of-day helpers
# ---------------------------------------------------------------------------

def _time_pressure() -> float:
    """Returns a multiplier (0.6–1.4) based on hour of day."""
    hour = datetime.now().hour
    if 8 <= hour <= 10 or 18 <= hour <= 21:
        return 1.35
    elif 0 <= hour <= 5:
        return 0.65
    else:
        return 1.0


def _seed_from_time(salt: int = 0) -> int:
    """Returns a seed that changes every 30s for deterministic but evolving data."""
    t = datetime.now()
    return (t.year * 10000 + t.month * 100 + t.day) * 10000 + (t.hour * 60 + t.minute) * 2 + (t.second // 30) + salt


# ---------------------------------------------------------------------------
# Hospital status — async with E-Gen fallback to mock
# ---------------------------------------------------------------------------

async def get_hospital_statuses(http_client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
    """
    Get hospital statuses. Uses E-Gen API if available, otherwise mock data.
    """
    egen_data = None
    if http_client:
        egen_client = EGenClient(http_client)
        egen_data = await egen_client.fetch_hospital_beds()

    if egen_data:
        logger.info("Using E-Gen live data for %d hospitals", len(egen_data))
        return _build_statuses_from_egen(egen_data)
    else:
        return _build_statuses_mock()


def _build_statuses_from_egen(egen_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build hospital statuses from real E-Gen API data."""
    results = []
    for h in HOSPITALS:
        hid = h["id"]
        api = egen_data.get(hid)

        if api:
            # Real data: compute occupancy from available ER beds vs total
            hvec = api.get("hvec", 0)
            total = h["total_beds"]
            available_beds = max(0, hvec)
            occupancy = max(0.05, min(0.97, 1 - (available_beds / total) if total > 0 else 0.80))
            status_index = round(max(3, min(98, (1 - occupancy) * 100)))
            data_source = "egen"

            # Equipment availability from API
            equipment = list(h["equipment"])
            if api.get("hvctayn") == "N" and "CT" in equipment:
                equipment.remove("CT")
            if api.get("hvmriayn") == "N" and "MRI" in equipment:
                equipment.remove("MRI")
        else:
            # Fallback to mock for this specific hospital
            mock = _mock_single_hospital(h, HOSPITALS.index(h))
            available_beds = mock["available_beds"]
            occupancy = mock["occupancy_pct"] / 100
            status_index = mock["status_index"]
            equipment = h["equipment"]
            data_source = "mock"

        # Status label
        if status_index >= 60:
            status = "green"
        elif status_index >= 30:
            status = "amber"
        else:
            status = "red"

        # Trend: compare with base load (simplified when using real data)
        base_occ = h.get("base_load", 0.60)
        if occupancy < base_occ - 0.05:
            trend = "improving"
        elif occupancy > base_occ + 0.05:
            trend = "worsening"
        else:
            trend = "stable"

        # Specialties (keep all available when using real data)
        all_specs = h["specialties"][:]
        rng = random.Random(_seed_from_time(salt=HOSPITALS.index(h) * 17))
        offline_count = rng.randint(0, min(1, len(all_specs) - 1))
        offline_specs = rng.sample(all_specs, offline_count) if data_source == "mock" else []
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
            "equipment_available": equipment,
            "data_source": data_source,
            "last_updated": datetime.now().isoformat(),
        })

    return results


def _build_statuses_mock() -> List[Dict[str, Any]]:
    """Build hospital statuses from mock simulation (original logic)."""
    tod_pressure = _time_pressure()
    results = []

    for i, h in enumerate(HOSPITALS):
        result = _mock_single_hospital(h, i)
        result["data_source"] = "mock"
        results.append(result)

    return results


def _mock_single_hospital(h: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Generate mock status for a single hospital."""
    tod_pressure = _time_pressure()
    rng = random.Random(_seed_from_time(salt=index * 17))

    base_load: float = h.get("base_load", 0.60)
    tod_delta = (tod_pressure - 1.0) * 0.20
    noise = rng.uniform(-0.08, 0.08)
    occupancy = max(0.05, min(0.97, base_load + tod_delta + noise))
    available_beds = max(0, round(h["total_beds"] * (1 - occupancy)))
    status_index = round(max(3, min(98, (1 - occupancy) * 100)))

    # Trend
    prev_rng = random.Random(_seed_from_time(salt=index * 17) - 1)
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

    # Specialties
    all_specs = h["specialties"][:]
    offline_count = rng.randint(0, min(1, len(all_specs) - 1))
    offline_specs = rng.sample(all_specs, offline_count)
    available_specs = [s for s in all_specs if s not in offline_specs]

    return {
        **h,
        "available_beds": available_beds,
        "occupancy_pct": round(occupancy * 100, 1),
        "status_index": status_index,
        "status": status,
        "trend": trend,
        "available_specialties": available_specs,
        "offline_specialties": offline_specs,
        "last_updated": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# OSINT alerts — async with Traffic API fallback to mock
# ---------------------------------------------------------------------------

async def get_osint_alerts(
    count: int = 8,
    http_client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    Get OSINT alerts. Combines real traffic incidents with mock SNS/weather/event alerts.
    """
    alerts: List[Dict[str, Any]] = []

    # Try real traffic data
    if http_client:
        traffic_client = TrafficClient(http_client)
        incidents = await traffic_client.fetch_incidents()
        if incidents:
            now = datetime.now()
            for i, inc in enumerate(incidents[:count]):
                alerts.append({
                    "id": f"traffic-live-{i}",
                    "type": inc["type"],
                    "severity": inc["severity"],
                    "message": inc["message"],
                    "timestamp": inc["timestamp"] or now.isoformat(),
                    "minutes_ago": inc["minutes_ago"],
                    "road_name": inc.get("road_name", ""),
                    "data_source": "traffic_api",
                })

    # Fill remaining slots with mock alerts
    remaining = count - len(alerts)
    if remaining > 0:
        mock_alerts = _mock_osint_alerts(remaining)
        alerts.extend(mock_alerts)

    alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return alerts[:count]


def _mock_osint_alerts(count: int) -> List[Dict[str, Any]]:
    """Generate mock OSINT alerts (original logic)."""
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
            "data_source": "mock",
        })
    alerts.sort(key=lambda x: x["timestamp"], reverse=True)
    return alerts
