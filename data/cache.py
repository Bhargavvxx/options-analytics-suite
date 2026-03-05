"""
In-memory data cache with TTL and staleness checks.

Thread-safe (uses a simple ``threading.Lock``).  The Streamlit layer
can use ``@st.cache_data`` *on top of* this for its own re-render
de-duplication; this cache lives below the UI.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from config.settings import Settings

_CFG = Settings()


@dataclass
class _CacheEntry:
    value: Any
    timestamp: float  # time.time()
    ttl: int          # seconds


class DataCache:
    """Simple TTL-based in-memory cache."""

    def __init__(self, default_ttl: int | None = None):
        self._store: Dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl or _CFG.data_cache_ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.time() - entry.timestamp > entry.ttl:
                del self._store[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            self._store[key] = _CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl or self._default_ttl,
            )

    def is_stale(self, key: str, threshold: int | None = None) -> bool:
        """Return True if the entry is older than *threshold* seconds."""
        threshold = threshold or _CFG.data_stale_threshold_seconds
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return True
            return (time.time() - entry.timestamp) > threshold

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
