"""
forecaster.py
Demand forecasting logic for the 분당 골든패스.
Rule-based for Phase 1; designed to be replaced with an ML model in Phase 2.
Now integrates real weather data from KMA API when available.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from services.api_clients.kma import KMAClient

logger = logging.getLogger(__name__)


def _time_of_day_factor() -> float:
    hour = datetime.now().hour
    if 8 <= hour <= 10 or 18 <= hour <= 21:
        return 1.30
    elif 0 <= hour <= 5:
        return 0.70
    return 1.0


def _alert_pressure(alerts: List[Dict[str, Any]]) -> float:
    """Compute extra demand pressure from OSINT alerts."""
    score = 0.0
    for alert in alerts:
        if alert["severity"] == "high":
            score += 0.15
        elif alert["severity"] == "medium":
            score += 0.07
        else:
            score += 0.02
    return min(score, 0.40)


async def get_weather_pressure(http_client: Optional[httpx.AsyncClient] = None) -> float:
    """
    Get weather-based pressure from KMA API.
    Returns 0.0–0.3 pressure score. Falls back to 0.0 if unavailable.
    """
    if not http_client:
        return 0.0
    try:
        kma_client = KMAClient(http_client)
        weather = await kma_client.fetch_weather()
        if weather:
            return weather.get("pressure_score", 0.0)
    except Exception:
        logger.exception("Weather pressure fetch failed")
    return 0.0


async def adjust_status_index(
    base_status_index: int,
    alerts: List[Dict[str, Any]],
    http_client: Optional[httpx.AsyncClient] = None,
) -> int:
    """
    Apply demand forecasting adjustments to the raw Status Index.
    Integrates time-of-day, alert pressure, and weather pressure.
    Returns an adjusted 0-100 score.
    """
    tod = _time_of_day_factor()
    alert_p = _alert_pressure(alerts)
    weather_p = await get_weather_pressure(http_client)

    pressure_total = (tod - 1.0) + alert_p + weather_p
    adjusted = base_status_index * (1 - pressure_total * 0.3)
    return max(3, min(98, round(adjusted)))


async def forecast_demand_narrative(
    alerts: List[Dict[str, Any]],
    http_client: Optional[httpx.AsyncClient] = None,
) -> str:
    """Return a short human-readable demand forecast narrative."""
    tod = _time_of_day_factor()
    alert_p = _alert_pressure(alerts)
    weather_p = await get_weather_pressure(http_client)

    total_pressure = alert_p + weather_p

    if tod >= 1.25 and total_pressure >= 0.20:
        return "🔴 피크 타임 + 다수 OSINT 경보 — 전반적 포화 가능성 높음"
    elif total_pressure >= 0.20:
        return "🟠 복수 사고 감지 — 권역 응급실 수요 급증 예상"
    elif tod >= 1.25:
        return "🟡 피크 타임 진입 — 혼잡도 상승 중"
    elif weather_p >= 0.15:
        return "🟡 악천후 감지 — 외상 수요 증가 예상"
    elif tod <= 0.75:
        return "🟢 야간 조용한 시간대 — 전반적 여유 상태"
    else:
        return "🟢 정상 운영 중 — 특이 사항 없음"
