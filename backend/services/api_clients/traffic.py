"""
traffic.py — ITS (국가교통정보센터) traffic incident API client.
Fetches real-time traffic incidents near Bundang area.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from config import get_settings
from services.cache import cache

logger = logging.getLogger(__name__)

# Bounding box for greater Bundang/Seongnam area
BUNDANG_BBOX = {
    "minX": "127.00",
    "maxX": "127.20",
    "minY": "37.30",
    "maxY": "37.50",
}

# Event type mapping
EVENT_TYPES = {
    "acc": "사고",
    "cor": "공사",
    "wea": "기상",
    "ete": "기타",
    "dis": "재해",
}


class TrafficClient:
    def __init__(self, http_client: httpx.AsyncClient):
        self._http = http_client
        self._settings = get_settings()

    async def fetch_incidents(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch real-time traffic incidents near Bundang.
        Returns list of incident dicts or None on failure.
        """
        if not self._settings.use_traffic:
            return None

        cached = cache.get("traffic:incidents")
        if cached is not None:
            return cached

        try:
            result = await self._fetch()
            if result is not None:
                cache.set("traffic:incidents", result, self._settings.cache_ttl_traffic)
            return result
        except Exception:
            logger.exception("Traffic API fetch failed")
            return None

    async def _fetch(self) -> Optional[List[Dict[str, Any]]]:
        # apiKey must not be double-encoded — build URL with raw key
        base = f"{self._settings.traffic_base_url}/getTIIS"
        url = f"{base}?apiKey={self._settings.traffic_api_key}"
        params = {
            "type": "all",
            "eventType": "all",
            "getType": "json",
            **BUNDANG_BBOX,
        }

        resp = await self._http.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        header = data.get("response", {}).get("header", {})
        if header.get("resultCode") != "0":
            logger.warning("Traffic API error: %s", header.get("resultMsg"))
            return None

        items = data.get("response", {}).get("body", {}).get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if not isinstance(items, list):
            items = [items] if items else []

        return [self._parse_item(item) for item in items]

    def _parse_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        event_type = item.get("eventType", "ete")
        start_raw = item.get("startDate", "")

        # Parse timestamp (format: YYYYMMDDHH24MISS)
        timestamp = ""
        minutes_ago = 0
        if start_raw and len(start_raw) >= 14:
            try:
                dt = datetime.strptime(start_raw[:14], "%Y%m%d%H%M%S")
                timestamp = dt.isoformat()
                minutes_ago = max(0, int((datetime.now() - dt).total_seconds() / 60))
            except ValueError:
                pass

        # Derive severity from event type
        severity = "medium"
        if event_type == "acc":
            severity = "high"
        elif event_type == "dis":
            severity = "high"
        elif event_type == "cor":
            severity = "low"

        return {
            "type": "traffic",
            "severity": severity,
            "message": item.get("message", f"{EVENT_TYPES.get(event_type, '교통')} 돌발상황"),
            "road_name": item.get("roadName", ""),
            "event_type": event_type,
            "lat": _float(item.get("coordY")),
            "lng": _float(item.get("coordX")),
            "timestamp": timestamp,
            "minutes_ago": minutes_ago,
        }


def _float(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
