"""Focused unit coverage for BIMA normalization and JIT provisioning."""

from domain.enums import UserRole
from services.bima_client import _profile


def test_bima_role_mapping() -> None:
    assert _profile({"id": 1, "email": "admin@test.local", "name": "Admin", "roles": ["super-administrator"]})["role"] == UserRole.SUPERUSER
    assert _profile({"id": 2, "email": "engineer@test.local", "name": "Engineer", "roles": ["engineer"]})["role"] == UserRole.ENGINEER
    assert _profile({"id": 3, "email": "lead@test.local", "name": "Lead", "position": "Lead Engineer"})["role"] == UserRole.LEAD_ENGINEER


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
