"""Redis-backed integration smoke test for the upload -> extract -> status slice.

Opt-in: set RUN_REDIS_INTEGRATION=1 with Postgres/Redis available and migrated.
Skipped in CI, where the compose services are not provisioned. Spawns a real
uvicorn API and a solo Celery worker so the full queue round-trip is exercised.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PDF = (
    Path(__file__).resolve().parents[2] / "docs" / "testcase" / (
        "05.MEPG-Asset Life Extension 2026_Static Equipment_RevB.pdf"
    )
)
API_URL = "http://127.0.0.1:8010"

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_REDIS_INTEGRATION") != "1",
    reason="requires migrated Postgres and running Redis (RUN_REDIS_INTEGRATION=1)",
)

TERMINAL = {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"}


def _spawn(*args: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, *args],
        cwd=BACKEND_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_upload_to_extraction_vertical_slice() -> None:
    """A valid upload reaches a terminal status with a persisted stage run."""

    if not SAMPLE_PDF.exists():
        pytest.skip("sample PDF fixture missing")

    api = _spawn("-m", "uvicorn", "main:app", "--port", "8010")
    worker = _spawn("-m", "celery", "-A", "core.celery_app", "worker", "--pool=solo")
    try:
        with httpx.Client() as client:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    client.get(f"{API_URL}/health")
                    break
                except httpx.TransportError:
                    time.sleep(1)
            else:
                pytest.fail("API server did not become ready")

            with SAMPLE_PDF.open("rb") as handle:
                response = client.post(
                    f"{API_URL}/api/v1/documents/upload",
                    files={"file": ("sample.pdf", handle, "application/pdf")},
                )
            assert response.status_code in (200, 201), response.text

            document_id = response.json()["id"]

            status_payload = {}
            for _ in range(30):
                status_payload = client.get(
                    f"{API_URL}/api/v1/documents/{document_id}/status"
                ).json()
                if status_payload["status"] in TERMINAL:
                    break
                time.sleep(1)

            assert status_payload["status"] in {
                "COMPLETED",
                "COMPLETED_WITH_WARNINGS",
            }, status_payload
            stage_names = {stage["name"] for stage in status_payload["stages"]}
            assert {"extraction", "revision_sync"} <= stage_names
    finally:
        worker.terminate()
        api.terminate()
        for proc in (worker, api):
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
