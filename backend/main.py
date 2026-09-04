"""
Document QC & Traceability Audit — FastAPI Application Entry Point
"""
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from api.dictionary import router as dictionary_router
from api.documents import router as documents_router
from api.issues import router as issues_router
from api.standards import router as standards_router
from core.config import settings
from core.errors import (
    FeatureNotReadyError,
    feature_not_ready_handler,
    http_error_handler,
    validation_error_handler,
)

app = FastAPI(
    title="Document QC API",
    description="Automated first-pass quality review of engineering documents (PDF/DOCX)",
    version="0.1.0",
)

# CORS — allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(FeatureNotReadyError, feature_not_ready_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


app.include_router(documents_router, prefix="/api/v1")
app.include_router(issues_router, prefix="/api/v1")
app.include_router(dictionary_router, prefix="/api/v1")
app.include_router(standards_router, prefix="/api/v1")
