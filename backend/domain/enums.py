"""Stable vocabulary used at API and persistence boundaries."""

from enum import StrEnum


class DocumentStatus(StrEnum):
    """Processing lifecycle for an uploaded document."""

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"


class ReviewStatus(StrEnum):
    """Human review lifecycle, kept separate from processing status."""

    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REVISION_REQUIRED = "REVISION_REQUIRED"


class StageStatus(StrEnum):
    """Lifecycle of one versioned pipeline stage run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    SUCCEEDED_WITH_WARNINGS = "SUCCEEDED_WITH_WARNINGS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class IssueCategory(StrEnum):
    """Top-level issue grouping used by API filters and the review UI."""

    LINGUISTIC = "LINGUISTIC"
    TRACEABILITY = "TRACEABILITY"
    SYSTEM = "SYSTEM"


class Severity(StrEnum):
    """Ordered human-facing issue severity labels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Decision(StrEnum):
    """QA decision applied to a detected issue."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"
    FLAGGED = "FLAGGED"


class Disposition(StrEnum):
    """Lead Reviewer disposition for audit-sensitive findings."""

    JUSTIFIED_EXCEPTION = "JUSTIFIED_EXCEPTION"
    REQUIRES_CORRECTION = "REQUIRES_CORRECTION"
