"""
Standards Registry API — admin-managed code patterns.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/standards-registry", tags=["standards"])


# POST /api/v1/standards-registry
