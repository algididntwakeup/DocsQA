"""Structured application logging with request correlation context."""

from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

correlation_id_context: ContextVar[str] = ContextVar("correlation_id", default="-")
request_path_context: ContextVar[str] = ContextVar("request_path", default="-")


class StructuredLogFormatter(logging.Formatter):
    """Serialize log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "correlation_id": getattr(record, "correlation_id", correlation_id_context.get()),
            "path": getattr(record, "path", request_path_context.get()),
            "logger": record.name,
            "message": record.getMessage(),
        }
        client_error = getattr(record, "client_error", None)
        if client_error is not None:
            payload["client_error"] = client_error
        exception_type = getattr(record, "exception_type", None)
        if exception_type is not None:
            payload["exception_type"] = exception_type
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """Install the structured formatter for application and server loggers."""

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler())
    formatter = StructuredLogFormatter()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        server_logger = logging.getLogger(name)
        for handler in server_logger.handlers:
            handler.setFormatter(formatter)
