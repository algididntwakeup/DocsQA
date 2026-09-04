"""
Documents API — upload, status, export.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/documents", tags=["documents"])


# POST /api/v1/documents/upload
# GET  /api/v1/documents/{id}/status
# GET  /api/v1/documents/{id}/issues?category=linguistic|traceability
# GET  /api/v1/documents/{id}/export?format=pdf|xlsx
# GET  /api/v1/documents/{id}/traceability-summary
