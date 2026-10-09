"""Request correlation and browser error ingestion tests."""

import json
import logging
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import LogCaptureFixture

from api.logs import router as logs_router
from core.exceptions import internal_server_error_handler
from core.logging import StructuredLogFormatter
from core.middleware import CorrelationIDMiddleware


def _test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)
    app.add_exception_handler(Exception, internal_server_error_handler)
    app.include_router(logs_router, prefix="/api/v1")
    return app


def test_correlation_id_is_returned_from_request_header() -> None:
    app = _test_app()

    @app.get("/ok")
    async def ok() -> dict[str, bool]:
        return {"success": True}

    response = TestClient(app).get("/ok", headers={"X-Correlation-ID": "trace-123"})

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "trace-123"


def test_missing_correlation_id_generates_uuid4() -> None:
    app = _test_app()

    @app.get("/ok")
    async def ok() -> dict[str, bool]:
        return {"success": True}

    response = TestClient(app).get("/ok")

    assert response.status_code == 200
    UUID(response.headers["X-Correlation-ID"], version=4)


def test_client_error_is_logged_with_its_trace_id(caplog: LogCaptureFixture) -> None:
    app = _test_app()
    client = TestClient(app)
    trace_id = "browser-error-42"
    caplog.set_level(logging.ERROR, logger="api.logs")

    response = client.post(
        "/api/v1/logs/client",
        headers={"X-Correlation-ID": trace_id},
        json={
            "message": "Test frontend crash",
            "stack": "Error: Test frontend crash",
            "component_stack": "at BrokenWidget",
            "url": "http://test/workspace/1",
            "user_agent": "test-agent",
            "correlation_id": trace_id,
            "timestamp": "2026-10-09T00:00:00Z",
        },
    )

    assert response.status_code == 202
    assert response.headers["X-Correlation-ID"] == trace_id
    assert response.json() == {"success": True, "correlation_id": trace_id}
    client_error = next(record for record in caplog.records if record.name == "api.logs")
    assert "[CLIENT_ERROR] Test frontend crash" in client_error.getMessage()
    assert client_error.__dict__["correlation_id"] == trace_id
    assert client_error.__dict__["client_error"]["component_stack"] == "at BrokenWidget"
    structured_error = json.loads(StructuredLogFormatter().format(client_error))
    assert structured_error["level"] == "ERROR"
    assert structured_error["correlation_id"] == trace_id
    assert structured_error["path"] == "/api/v1/logs/client"
    assert structured_error["timestamp"].endswith("Z")


def test_uncaught_error_returns_correlated_standard_response(caplog: LogCaptureFixture) -> None:
    app = _test_app()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("private exception detail")

    trace_id = "server-error-77"
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom", headers={"X-Correlation-ID": trace_id})

    assert response.status_code == 500
    assert response.headers["X-Correlation-ID"] == trace_id
    assert response.json() == {
        "success": False,
        "error_code": "INTERNAL_SERVER_ERROR",
        "message": "Terjadi kesalahan internal pada server",
        "correlation_id": trace_id,
    }
    assert "private exception detail" not in response.text
    error_record = next(
        record for record in caplog.records if record.name == "core.exceptions"
    )
    assert error_record.__dict__["correlation_id"] == trace_id
    assert error_record.exc_info is not None
    assert "test_telemetry.py" in logging.Formatter().formatException(error_record.exc_info)
    structured_error = json.loads(StructuredLogFormatter().format(error_record))
    assert structured_error["path"] == "/boom"
    assert structured_error["correlation_id"] == trace_id
    assert "private exception detail" in structured_error["exception"]
