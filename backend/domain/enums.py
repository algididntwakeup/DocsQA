"""Stable vocabulary used at API and persistence boundaries."""

from enum import StrEnum


class DocumentStatus(StrEnum):
    """Processing lifecycle for an uploaded document."""

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"


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
