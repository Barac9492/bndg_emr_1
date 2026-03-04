"""
cache.py — Simple in-memory TTL cache for API responses.
"""

import time
from typing import Any, Optional


class TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        self._store.clear()


# Singleton instance
cache = TTLCache()
