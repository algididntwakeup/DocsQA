"""Application exceptions and RFC 9457 response handlers."""

from typing import NoReturn

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas.common import FieldViolation, ProblemDetail


class FeatureNotReadyError(RuntimeError):
    """Raised by contract-first endpoints whose implementation is pending."""

    def __init__(self, feature: str) -> None:
        super().__init__(f"{feature} is not implemented yet.")
        self.feature = feature


class UploadRejectedError(ValueError):
    """Raised when an upload violates a safe, public validation rule."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def feature_not_ready(feature: str) -> NoReturn:
    """Raise the standard error used by deliberately unfinished endpoints."""

    raise FeatureNotReadyError(feature)


def _problem_response(problem: ProblemDetail) -> JSONResponse:
    """Serialize a problem document with the correct media type."""

    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(mode="json", exclude_none=True),
        media_type="application/problem+json",
    )


async def feature_not_ready_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Return an explicit 501 response instead of placeholder success data."""

    assert isinstance(exc, FeatureNotReadyError)
    return _problem_response(
        ProblemDetail(
            type="urn:docqc:error:FEATURE_NOT_READY",
            title="Feature not ready",
            status=501,
            detail=str(exc),
            instance=str(request.url.path),
            code="FEATURE_NOT_READY",
        )
    )


async def upload_rejected_handler(request: Request, exc: Exception) -> JSONResponse:
    """Map a safe upload validation failure to a public problem document."""

    assert isinstance(exc, UploadRejectedError)
    return _problem_response(
        ProblemDetail(
            type=f"urn:docqc:error:{exc.code}",
            title="Upload rejected",
            status=422,
            detail=exc.detail,
            instance=str(request.url.path),
            code=exc.code,
        )
    )


async def validation_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Normalize FastAPI validation failures into the public error contract."""

    assert isinstance(exc, RequestValidationError)
    violations = [
        FieldViolation(
            field=".".join(str(part) for part in error["loc"]),
            message=error["msg"],
            code=error["type"],
        )
        for error in exc.errors()
    ]
    return _problem_response(
        ProblemDetail(
            type="urn:docqc:error:VALIDATION_ERROR",
            title="Request validation failed",
            status=422,
            detail="One or more request values are invalid.",
            instance=str(request.url.path),
            code="VALIDATION_ERROR",
            errors=violations,
        )
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Normalize framework HTTP exceptions into the public error contract."""

    assert isinstance(exc, HTTPException)
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _problem_response(
        ProblemDetail(
            type=f"urn:docqc:error:HTTP_{exc.status_code}",
            title="HTTP request failed",
            status=exc.status_code,
            detail=detail,
            instance=str(request.url.path),
            code=f"HTTP_{exc.status_code}",
        )
    )
