import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Optional


class TTLLRUCache:
    """
    Tiny in-memory TTL + LRU cache.

    - TTL bounds staleness.
    - LRU bounds memory growth.
    - Thread-safe for simple concurrent access.
    """

    def __init__(self, *, max_entries: int, ttl_seconds: Optional[int] = None):
        self.max_entries = max(1, int(max_entries))
        self.ttl_seconds = ttl_seconds
        self._data: "OrderedDict[str, tuple[Any, float]]" = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            if key not in self._data:
                return None

            value, expires_at = self._data[key]
            if expires_at is not None and now > expires_at:
                # Expired: remove and behave like a miss.
                del self._data[key]
                return None

            # Refresh LRU position
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        now = time.time()
        with self._lock:
            expires_at = None
            if self.ttl_seconds is not None:
                expires_at = now + float(self.ttl_seconds)

            self._data[key] = (value, expires_at)
            self._data.move_to_end(key)

            # Evict LRU entries
            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)

    def pop(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

