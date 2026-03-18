import json
import logging
import os
import sys
import time
from typing import Any, Dict


class JsonLogFormatter(logging.Formatter):
    """Very small JSON logger formatter (no external deps)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": int(time.time() * 1000),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # If extra fields were supplied, include them.
        # Convention: request_id can be added via logger.{info,warn,error}(..., extra={...})
        for key in ("request_id", "path", "method", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Avoid breaking JSON by ensuring all values are serializable.
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    """Configure application-wide structured logs."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(log_level)

    # If called multiple times (e.g. in reload), don't duplicate handlers.
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)


def get_logger(name: str = "app"):
    """Central logger accessor used across the codebase."""
    return logging.getLogger(name)

