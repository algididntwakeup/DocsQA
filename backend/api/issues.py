"""
Issues API — decision, disposition.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/issues", tags=["issues"])


# PATCH /api/v1/issues/{id}/decision
# PATCH /api/v1/issues/{id}/disposition
