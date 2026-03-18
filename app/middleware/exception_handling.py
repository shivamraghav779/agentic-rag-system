import requests
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logging import get_logger


logger = get_logger("app.http")


def _extract_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("x-request-id") or ""


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """Global exception-to-JSON mapper (DB + LLM + standard exceptions)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = _extract_request_id(request)
        try:
            return await call_next(request)

        except HTTPException as exc:
            detail = exc.detail if exc.detail is not None else "Request error"
            logger.warning(
                "http_error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": exc.status_code,
                },
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": detail, "request_id": request_id},
                headers={"X-Request-Id": request_id},
            )

        except SQLAlchemyError as exc:
            # Central DB error mapping (prevents leaking internal stack traces)
            logger.exception(
                "database_error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Database error", "request_id": request_id},
                headers={"X-Request-Id": request_id},
            )

        # Google API / Gemini errors are surfaced as google.api_core exceptions.
        except Exception as exc:
            # Group by type via dynamic imports to keep startup resilient.
            try:
                from google.api_core import exceptions as google_exceptions  # type: ignore

                if isinstance(exc, google_exceptions.ResourceExhausted):
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "LLM rate limit exceeded", "request_id": request_id},
                        headers={"X-Request-Id": request_id},
                    )
                if isinstance(exc, google_exceptions.GoogleAPIError):
                    return JSONResponse(
                        status_code=502,
                        content={"detail": "Upstream LLM error", "request_id": request_id},
                        headers={"X-Request-Id": request_id},
                    )
            except Exception:
                # ignore if google is not importable in this environment
                pass

            # Groq/requests timeouts and HTTP errors
            if isinstance(exc, requests.exceptions.Timeout):
                return JSONResponse(
                    status_code=504,
                    content={"detail": "LLM request timed out", "request_id": request_id},
                    headers={"X-Request-Id": request_id},
                )

            if isinstance(exc, requests.exceptions.HTTPError):
                status_code = getattr(exc, "status_code", None) or 502
                if status_code == 429:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "LLM rate limit exceeded", "request_id": request_id},
                        headers={"X-Request-Id": request_id},
                    )
                return JSONResponse(
                    status_code=502,
                    content={"detail": "Upstream service error", "request_id": request_id},
                    headers={"X-Request-Id": request_id},
                )

            # Fallback: standard exception
            logger.exception(
                "unhandled_exception",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
                headers={"X-Request-Id": request_id},
            )

