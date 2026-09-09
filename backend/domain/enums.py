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
    LAYOUT = "LAYOUT"
    BUDINSKI = "BUDINSKI"
    SPELLING = "SPELLING"
    GRAMMAR = "GRAMMAR"
    DICTIONARY = "DICTIONARY"
    STANDARD_TRACEABILITY = "STANDARD_TRACEABILITY"


class EvaluationStatus(StrEnum):
    """Deterministic verdict for a numeric-claim check against a benchmark expectation."""

    CORRECT = "CORRECT"
    ROUNDING_BOUNDARY = "ROUNDING_BOUNDARY"
    MISMATCH = "MISMATCH"


class Severity(StrEnum):
    """Ordered human-facing issue severity labels."""

    BLOCKER = "BLOCKER"
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"

    # Backward-compatible aliases for existing tests/fixtures
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


IssueSeverity = Severity


def cap_linguistic_severity(severity: Severity | str) -> Severity:
    """Keep language findings below the dashboard's high-priority tiers."""
    value = severity.value if isinstance(severity, Severity) else str(severity)
    if value == Severity.INFO.value:
        return Severity.INFO
    return Severity.MINOR


class PipelineStage(StrEnum):
    """Canonical document review pipeline stages."""

    EXTRACTING = "EXTRACTING"
    LAYOUT_INSPECTION = "LAYOUT_INSPECTION"
    BUDINSKI_AUDIT = "BUDINSKI_AUDIT"
    STANDARDS_CHECK = "STANDARDS_CHECK"
    LINGUISTIC_CHECK = "LINGUISTIC_CHECK"
    AGGREGATING = "AGGREGATING"


StageName = PipelineStage
