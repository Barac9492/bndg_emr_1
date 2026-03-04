"""
egen.py — E-Gen (응급의료포털) API client.
Fetches real-time emergency room available bed info.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx

from config import get_settings
from services.cache import cache

logger = logging.getLogger(__name__)

# Map our hospital IDs to E-Gen institution names for matching
HOSPITAL_NAME_MAP: Dict[str, str] = {
    "bsuh": "분당서울대학교병원",
    "cha": "분당차병원",
    "jss": "제생병원",
    "ysei": "연세대학교의과대학용인세브란스병원",
    "snmc": "성남시의료원",
    "kcha": "강남차병원",  # Not in E-Gen — uses mock fallback
}

# Region queries needed to cover all our hospitals
REGION_QUERIES = [
    {"STAGE1": "경기도", "STAGE2": "성남시 분당구"},
    {"STAGE1": "경기도", "STAGE2": "성남시 수정구"},
    {"STAGE1": "경기도", "STAGE2": "성남시 중원구"},
    {"STAGE1": "경기도", "STAGE2": "용인시 기흥구"},
]


class EGenClient:
    def __init__(self, http_client: httpx.AsyncClient):
        self._http = http_client
        self._settings = get_settings()

    async def fetch_hospital_beds(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Fetch real-time bed availability from E-Gen API.
        Returns dict keyed by our hospital ID, or None on failure.
        """
        if not self._settings.use_egen:
            return None

        cached = cache.get("egen:beds")
        if cached is not None:
            return cached

        try:
            all_items = await self._fetch_all_regions()
            result = self._match_hospitals(all_items)
            if result:
                cache.set("egen:beds", result, self._settings.cache_ttl_egen)
            return result or None
        except Exception:
            logger.exception("E-Gen API fetch failed")
            return None

    async def _fetch_all_regions(self) -> List[ET.Element]:
        """Fetch bed data from all relevant regions."""
        all_items: List[ET.Element] = []
        for region in REGION_QUERIES:
            items = await self._fetch_region(region["STAGE1"], region["STAGE2"])
            all_items.extend(items)
        return all_items

    async def _fetch_region(self, stage1: str, stage2: str) -> List[ET.Element]:
        """Fetch a single region's emergency room data."""
        # serviceKey must not be double-encoded — build URL with raw key
        base = f"{self._settings.egen_base_url}/getEmrrmRltmUsefulSckbdInfoInqire"
        url = f"{base}?serviceKey={self._settings.egen_api_key}"
        params = {
            "STAGE1": stage1,
            "STAGE2": stage2,
            "pageNo": "1",
            "numOfRows": "50",
        }
        resp = await self._http.get(url, params=params, timeout=10.0)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        result_code = root.findtext(".//resultCode")
        if result_code != "00":
            logger.warning("E-Gen API error: %s", root.findtext(".//resultMsg"))
            return []

        return root.findall(".//item")

    def _match_hospitals(self, items: List[ET.Element]) -> Dict[str, Dict[str, Any]]:
        """Match E-Gen items to our hospital registry by name."""
        # Build reverse map: name -> our ID
        name_to_id = {v: k for k, v in HOSPITAL_NAME_MAP.items()}
        result: Dict[str, Dict[str, Any]] = {}

        for item in items:
            duty_name = (item.findtext("dutyName") or item.findtext("dutyname") or "").strip()
            # Try exact match first, then substring
            hospital_id = name_to_id.get(duty_name)
            if not hospital_id:
                for name, hid in name_to_id.items():
                    if name in duty_name or duty_name in name:
                        hospital_id = hid
                        break
            if not hospital_id:
                continue

            result[hospital_id] = {
                "hpid": item.findtext("hpid", ""),
                "hvec": _int(item.findtext("hvec")),        # ER available beds
                "hvoc": _int(item.findtext("hvoc")),        # OR available
                "hvcc": _int(item.findtext("hvcc")),        # Neuro ICU
                "hvncc": _int(item.findtext("hvncc")),      # Neonatal ICU
                "hvccc": _int(item.findtext("hvccc")),      # Thoracic ICU
                "hvicc": _int(item.findtext("hvicc")),      # General ICU
                "hvgc": _int(item.findtext("hvgc")),        # Inpatient ward
                "hvctayn": item.findtext("hvctayn", "N"),   # CT available
                "hvmriayn": item.findtext("hvmriayn", "N"), # MRI available
                "hvventiayn": item.findtext("hvventiayn", "N"),  # Ventilator
                "hvidate": item.findtext("hvidate", ""),    # Last update time
                "dutytel3": item.findtext("dutyTel3") or item.findtext("dutytel3") or "",
            }

        return result


def _int(val: Optional[str]) -> int:
    """Safe int parse, defaulting to 0."""
    if val is None:
        return 0
    try:
        return int(val)
    except ValueError:
        return 0
