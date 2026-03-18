import hashlib
import time
from threading import Lock
from typing import Callable, Dict, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory fixed-window rate limiter.

    Targets:
    - POST /api/v1/chat
    - POST /api/v1/chat/stream
    """

    def __init__(self, app, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self._lock = Lock()
        # key -> (window_start_epoch_seconds, count)
        self._counters: Dict[str, Tuple[float, int]] = {}

    def _key_for_request(self, request: Request) -> str:
        auth = request.headers.get("authorization") or ""
        token = auth.split(" ", 1)[1] if auth.lower().startswith("bearer ") and len(auth.split(" ", 1)) > 1 else ""
        if token:
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
        else:
            token_hash = "anon"

        ip = getattr(request.client, "host", None) or "unknown"
        return f"{ip}:{token_hash}"

    def _limit_for_path(self, path: str) -> int:
        if path == "/api/v1/chat":
            return int(settings.chat_rate_limit_per_minute)
        if path == "/api/v1/chat/stream":
            return int(settings.chat_stream_rate_limit_per_minute)
        return 0

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        limit = self._limit_for_path(request.url.path)
        if limit <= 0:
            return await call_next(request)

        window_seconds = 60.0
        now = time.time()
        key = self._key_for_request(request)
        request_id = getattr(request.state, "request_id", None)

        with self._lock:
            window_start, count = self._counters.get(key, (0.0, 0))
            if now - window_start >= window_seconds:
                window_start = now
                count = 0

            if count >= limit:
                retry_after = int(window_seconds - (now - window_start))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "request_id": request_id},
                    headers={
                        "X-Request-Id": request_id or "",
                        "Retry-After": str(max(1, retry_after)),
                    },
                )

            self._counters[key] = (window_start, count + 1)

        return await call_next(request)

