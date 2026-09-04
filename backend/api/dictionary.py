"""
Custom Engineering Dictionary API — CRUD + governance.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


# POST  /api/v1/dictionary/terms
# GET   /api/v1/dictionary/terms?scope=project:{id}
# PATCH /api/v1/dictionary/terms/{id}/approve
