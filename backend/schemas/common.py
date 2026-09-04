"""Cross-resource API schemas."""

from typing import Any

from pydantic import Field

from schemas.base import ApiModel


class FieldViolation(ApiModel):
    """One request-validation failure safe to expose to an API client."""

    field: str
    message: str
    code: str


class ProblemDetail(ApiModel):
    """RFC 9457-style error response with a stable application code."""

    type: str = "about:blank"
    title: str
    status: int = Field(ge=400, le=599)
    detail: str | None = None
    instance: str | None = None
    code: str
    errors: list[FieldViolation] = Field(default_factory=list)

    model_config = {
        "extra": "forbid",
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "type": "urn:docqc:error:FEATURE_NOT_READY",
                    "title": "Feature not ready",
                    "status": 501,
                    "detail": "Document upload is not implemented yet.",
                    "instance": "/api/v1/documents/upload",
                    "code": "FEATURE_NOT_READY",
                    "errors": [],
                }
            ]
        },
    }


class PageInfo(ApiModel):
    """Cursor-free pagination metadata for the initial API contract."""

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


JsonObject = dict[str, Any]
