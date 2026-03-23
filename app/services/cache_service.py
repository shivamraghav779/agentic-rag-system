"""Small in-memory TTL cache service."""

import threading
import time
from typing import Dict, Optional, Tuple


class CacheService:
    """Thread-safe TTL cache for short-lived responses."""

    def __init__(self, ttl_seconds: int = 60):
        self._ttl_seconds = max(1, ttl_seconds)
        self._store: Dict[str, Tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        """Get cached value if not expired."""
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expiry, value = item
            if expiry <= now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: str) -> None:
        """Set cached value."""
        expiry = time.time() + self._ttl_seconds
        with self._lock:
            self._store[key] = (expiry, value)

