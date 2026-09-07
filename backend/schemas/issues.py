"""Issue evidence, review decision, and disposition schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from domain.enums import IssueCategory, Severity
from schemas.base import ApiModel
from schemas.common import PageInfo


class BoundingBox(ApiModel):
    """PDF-point rectangle in the canonical top-left coordinate system."""

    page_index: int = Field(ge=0)
    x0: float = Field(ge=0)
    y0: float = Field(ge=0)
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)
    page_width: float = Field(gt=0)
    page_height: float = Field(gt=0)


class TextSpan(ApiModel):
    """Character offsets within normalized extracted page text."""

    page_index: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class EvidenceBase(ApiModel):
    """Version provenance shared by every evidence variant."""

    extractor_version: str
    rule_version: str


class TableMathEvidence(EvidenceBase):
    """Arithmetic operands and locations supporting a table finding."""

    kind: Literal["TABLE_MATH"] = "TABLE_MATH"
    computed_value: Decimal
    stated_value: Decimal
    delta: Decimal
    tolerance: Decimal
    operand_locations: list[BoundingBox]
    total_location: BoundingBox


class ReferenceDriftEvidence(EvidenceBase):
    """Referenced and actual page evidence for ToC/LoF/LoT drift."""

    kind: Literal["REFERENCE_DRIFT"] = "REFERENCE_DRIFT"
    label: str
    referenced_page_label: str
    actual_page_label: str
    page_delta: int
    entry_location: BoundingBox
    target_location: BoundingBox


class RevisionEvidence(EvidenceBase):
    """Three-way filename, cover, and revision-history evidence."""

    kind: Literal["REVISION"] = "REVISION"
    filename_revision: str | None
    cover_revision: str | None
    revision_sheet_revision: str | None
    sources_disagreeing: list[Literal["FILENAME", "COVER", "REVISION_SHEET"]]
    locations: list[BoundingBox]


class StandardEvidence(EvidenceBase):
    """Normalized body citation and bibliography evidence."""

    kind: Literal["STANDARD"] = "STANDARD"
    cited_standard: str
    body_edition_year: int | None = None
    bibliography_entry: str | None = None
    bibliography_edition_year: int | None = None
    body_location: BoundingBox
    bibliography_location: BoundingBox | None = None


class LinguisticEvidence(EvidenceBase):
    """Original span and optional replacement for language findings."""

    kind: Literal["LINGUISTIC"] = "LINGUISTIC"
    original_text: str
    suggestion: str | None = None
    location: BoundingBox | TextSpan
    original_location: BoundingBox | None = None


class StageFailureEvidence(EvidenceBase):
    """Sanitized pipeline-stage failure surfaced without losing other results."""

    kind: Literal["STAGE_FAILURE"] = "STAGE_FAILURE"
    stage: str
    error_code: str
    retryable: bool


class ReferenceRuleEvidence(EvidenceBase):
    """Provenance and parameters for reference standard rule findings."""

    kind: Literal["REFERENCE_RULE"] = "REFERENCE_RULE"
    standard: str
    edition: str
    clause: str
    standard_page: int
    rule_kind: str
    detected_parameter: str | None = None
    detected_value: str | None = None
    compliance_status: str = "NON_COMPLIANT"
    location: BoundingBox


IssueEvidence = Annotated[
    TableMathEvidence
    | ReferenceDriftEvidence
    | RevisionEvidence
    | StandardEvidence
    | LinguisticEvidence
    | StageFailureEvidence
    | ReferenceRuleEvidence,
    Field(discriminator="kind"),
]


class IssueRead(ApiModel):
    """Unified issue record consumed by the review UI."""

    id: UUID
    document_id: UUID
    category: IssueCategory
    type: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    message: str
    evidence: IssueEvidence
    included_in_report: bool = True
    reviewer_note: str | None = None
    # Compatibility-only response value; curation does not use optimistic locking.
    version: int = 1
    created_at: datetime
    updated_at: datetime


class IssueListResponse(ApiModel):
    """Paginated issue collection plus review summary counts."""

    issues: list[IssueRead]
    pagination: PageInfo
    counts_by_severity: dict[Severity, int]


class IssueCurationRequest(ApiModel):
    """Lightweight report curation; it is not an approval decision."""

    included_in_report: bool
    reviewer_note: str | None = Field(default=None, max_length=4000)
