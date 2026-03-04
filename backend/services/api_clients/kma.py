"""
kma.py — KMA (기상청) ultra-short-term weather observation client.
Fetches current weather data for the Bundang area.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

from config import get_settings
from services.cache import cache

logger = logging.getLogger(__name__)

# Bundang area grid coordinates (KMA Lambert grid)
BUNDANG_NX = 63
BUNDANG_NY = 124

# Weather category codes
CATEGORIES = {
    "T1H": "temperature",    # degrees C
    "RN1": "precipitation",  # mm (1-hour)
    "REH": "humidity",       # %
    "PTY": "precip_type",    # 0=none, 1=rain, 2=rain+snow, 3=snow, 5=drizzle, 6=rain+drizzle, 7=snow+drizzle
    "VEC": "wind_direction", # degrees
    "WSD": "wind_speed",     # m/s
}

# PTY code meanings
PRECIP_TYPES = {
    "0": "none",
    "1": "rain",
    "2": "rain_snow",
    "3": "snow",
    "5": "drizzle",
    "6": "rain_drizzle",
    "7": "snow_drizzle",
}


class KMAClient:
    def __init__(self, http_client: httpx.AsyncClient):
        self._http = http_client
        self._settings = get_settings()

    async def fetch_weather(self) -> Optional[Dict[str, Any]]:
        """
        Fetch current weather observation for Bundang.
        Returns parsed weather dict or None on failure.
        """
        if not self._settings.use_kma:
            return None

        cached = cache.get("kma:weather")
        if cached is not None:
            return cached

        try:
            result = await self._fetch()
            if result:
                cache.set("kma:weather", result, self._settings.cache_ttl_kma)
            return result
        except Exception:
            logger.exception("KMA API fetch failed")
            return None

    async def _fetch(self) -> Optional[Dict[str, Any]]:
        # Data is available ~40min after the hour, so use previous hour
        now = datetime.now()
        base_dt = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        base_date = base_dt.strftime("%Y%m%d")
        base_time = base_dt.strftime("%H00")

        url = f"{self._settings.kma_base_url}/getUltraSrtNcst"
        params = {
            "serviceKey": self._settings.kma_api_key,
            "pageNo": "1",
            "numOfRows": "10",
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": str(BUNDANG_NX),
            "ny": str(BUNDANG_NY),
        }

        resp = await self._http.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        header = data.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            logger.warning("KMA API error: %s", header.get("resultMsg"))
            return None

        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return self._parse_items(items, base_date, base_time)

    def _parse_items(self, items: list, base_date: str, base_time: str) -> Dict[str, Any]:
        weather: Dict[str, Any] = {
            "base_date": base_date,
            "base_time": base_time,
            "location": "분당구",
        }

        for item in items:
            cat = item.get("category", "")
            val = item.get("obsrValue", "")
            if cat in CATEGORIES:
                key = CATEGORIES[cat]
                if cat == "PTY":
                    weather[key] = PRECIP_TYPES.get(str(val), "unknown")
                    weather["precip_code"] = int(float(val))
                elif cat in ("T1H", "RN1", "WSD"):
                    weather[key] = float(val)
                elif cat in ("REH", "VEC"):
                    weather[key] = int(float(val))

        # Derive weather pressure score for forecaster
        weather["pressure_score"] = self._compute_pressure(weather)

        return weather

    @staticmethod
    def _compute_pressure(weather: Dict[str, Any]) -> float:
        """
        Compute a 0.0–0.3 weather pressure score for demand forecasting.
        Bad weather → more accidents → higher ER demand.
        """
        score = 0.0
        precip_code = weather.get("precip_code", 0)
        if precip_code in (1, 2, 6):       # rain
            score += 0.10
        elif precip_code in (3, 7):         # snow
            score += 0.15
        elif precip_code == 5:              # drizzle
            score += 0.05

        temp = weather.get("temperature", 15.0)
        if temp <= -5:
            score += 0.10       # extreme cold → slips, hypothermia
        elif temp <= 0:
            score += 0.05       # freezing → icy roads

        wind = weather.get("wind_speed", 0.0)
        if wind >= 14.0:
            score += 0.10       # strong wind → accidents
        elif wind >= 10.0:
            score += 0.05

        rain = weather.get("precipitation", 0.0)
        if rain >= 30.0:
            score += 0.10       # heavy rain
        elif rain >= 10.0:
            score += 0.05

        return min(score, 0.30)
