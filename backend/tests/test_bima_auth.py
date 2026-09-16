"""Focused unit coverage for BIMA normalization and JIT provisioning."""

import pytest

from domain.enums import UserRole
from services.bima_client import _profile, fetch_bima_projects


def test_bima_role_mapping() -> None:
    assert (
        _profile(
            {
                "id": 1,
                "email": "admin@test.local",
                "name": "Admin",
                "roles": ["super-administrator"],
            }
        )["role"]
        == UserRole.SUPERUSER
    )
    assert (
        _profile(
            {"id": 2, "email": "engineer@test.local", "name": "Engineer", "roles": ["engineer"]}
        )["role"]
        == UserRole.ENGINEER
    )
    assert (
        _profile(
            {"id": 3, "email": "lead@test.local", "name": "Lead", "position": "Lead Engineer"}
        )["role"]
        == UserRole.LEAD_ENGINEER
    )


def test_bima_envelope_profile_mapping() -> None:
    profile = _profile(
        {
            "success": True,
            "data": {
                "valid": True,
                "user": {
                    "bima_id": 42,
                    "username": "harry",
                    "name": "Harry Agustiana",
                    "email": "harry.agustiana@reksolindo.co.id",
                    "department": "Engineering",
                    "position": "Chief Technology Officer",
                    "roles": ["super-administrator"],
                    "is_admin": True,
                },
            },
        }
    )
    assert profile["bima_id"] == 42
    assert profile["full_name"] == "Harry Agustiana"
    assert profile["role"] == UserRole.SUPERUSER


@pytest.mark.anyio
async def test_fetch_bima_projects(monkeypatch) -> None:
    class Response:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"success": True, "data": {"projects": [{"id": 7, "code": "P-7", "name": "Plant 7"}]}}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, _url, headers):
            assert headers == {"Authorization": "Bearer bima-token"}
            return Response()

    monkeypatch.setattr("services.bima_client.httpx.AsyncClient", lambda **_kwargs: Client())
    assert await fetch_bima_projects("bima-token") == [{"id": 7, "code": "P-7", "name": "Plant 7"}]
