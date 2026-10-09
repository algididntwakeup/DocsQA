"""Focused unit coverage for BIMA normalization and JIT provisioning."""

from typing import Any

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


def test_bima_directory_profile_mapping() -> None:
    """Directory rows nest identity under ``profile`` and may lack a real email."""

    profile = _profile(
        {
            "id": 57,
            "username": "m.alghifari",
            "profile_id": 69,
            "profile": {
                "id": 69,
                "email": "m.alghifari@reksolindo.co.id",
                "full_name": "Muhammad Alghifari",
                "department": "Engineering",
                "role": None,
            },
        }
    )
    assert profile["bima_id"] == 57
    assert profile["email"] == "m.alghifari@reksolindo.co.id"
    assert profile["full_name"] == "Muhammad Alghifari"
    assert profile["department"] == "Engineering"
    assert profile["role"] == UserRole.ENGINEER

    username_only = _profile(
        {
            "id": 3,
            "username": "aswin",
            "profile": {"id": 4, "full_name": "Aswin", "department": None},
        }
    )
    assert username_only["bima_id"] == 3
    assert username_only["email"] == "aswin@bima.local"
    assert username_only["full_name"] == "Aswin"

@pytest.mark.anyio
async def test_fetch_bima_projects(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "success": True,
                "data": {"projects": [{"id": 7, "code": "P-7", "name": "Plant 7"}]},
            }

    class Client:
        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(self, *_args: Any) -> None:
            return None

        async def get(self, _url: str, headers: dict[str, str]) -> Response:
            assert headers == {"Authorization": "Bearer bima-token"}
            return Response()

    monkeypatch.setattr("services.bima_client.httpx.AsyncClient", lambda **_kwargs: Client())
    assert await fetch_bima_projects("bima-token") == [{"id": 7, "code": "P-7", "name": "Plant 7"}]


def test_bima_role_mapping_covers_internal_roles() -> None:
    """HR/GA and finance identities map to their own roles, not to engineer."""

    assert (
        _profile(
            {"id": 10, "email": "hr@test.local", "name": "HR", "roles": ["hrga"]}
        )["role"]
        == UserRole.HRGA
    )
    assert (
        _profile(
            {"id": 11, "email": "hrd@test.local", "name": "HRD", "roles": ["HRD"]}
        )["role"]
        == UserRole.HRGA
    )
    assert (
        _profile(
            {
                "id": 12,
                "email": "ga@test.local",
                "name": "GA",
                "department": "General Affair",
            }
        )["role"]
        == UserRole.HRGA
    )
    assert (
        _profile(
            {"id": 13, "email": "finance@test.local", "name": "Fin", "roles": ["finance"]}
        )["role"]
        == UserRole.FINANCE
    )
    assert (
        _profile(
            {
                "id": 14,
                "email": "acc@test.local",
                "name": "Acc",
                "department": "Accounting",
            }
        )["role"]
        == UserRole.FINANCE
    )


def test_bima_role_mapping_keeps_precedence_rules() -> None:
    """Existing precedence must not regress when domain tokens are added."""

    # A finance manager is finance, never a lead engineer.
    assert (
        _profile(
            {
                "id": 20,
                "email": "fm@test.local",
                "name": "Finance Manager",
                "position": "Finance Manager",
            }
        )["role"]
        == UserRole.FINANCE
    )
    # A plain manager still maps to lead engineer.
    assert (
        _profile(
            {"id": 21, "email": "pm@test.local", "name": "PM", "roles": ["manager"]}
        )["role"]
        == UserRole.LEAD_ENGINEER
    )
    # Admin claims still win over every domain token.
    assert (
        _profile(
            {
                "id": 22,
                "email": "admin@test.local",
                "name": "Admin",
                "is_admin": True,
                "roles": ["finance"],
            }
        )["role"]
        == UserRole.SUPERUSER
    )
    # Unrelated positions stay engineer.
    assert (
        _profile(
            {
                "id": 23,
                "email": "eng@test.local",
                "name": "Eng",
                "position": "Engineer",
                "department": "Engineering",
            }
        )["role"]
        == UserRole.ENGINEER
    )
    # "Legal" contains 'ga' as a substring but is not General Affair.
    assert (
        _profile(
            {"id": 24, "email": "legal@test.local", "name": "Legal", "position": "Legal Staff"}
        )["role"]
        == UserRole.ENGINEER
    )
