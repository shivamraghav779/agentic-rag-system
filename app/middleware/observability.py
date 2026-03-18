import json
import time
import uuid
from typing import Callable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.logging import get_logger


logger = get_logger("app.http")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Adds request_id, structured request logging, and centralized error handling.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.time()
        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start) * 1000)

            # Attach request_id so clients can correlate logs.
            response.headers["X-Request-Id"] = request_id

            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response

        except HTTPException as exc:
            duration_ms = int((time.time() - start) * 1000)
            logger.warning(
                "http_error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": exc.status_code,
                    "duration_ms": duration_ms,
                    "detail": exc.detail,
                },
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "detail": exc.detail,
                    "request_id": request_id,
                },
                headers={"X-Request-Id": request_id},
            )

        except Exception:
            duration_ms = int((time.time() - start) * 1000)
            logger.exception(
                "unhandled_error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                },
                headers={"X-Request-Id": request_id},
            )

