"""Pydantic schemas for deterministic linguistic findings and stage analyses."""

from pydantic import Field, field_validator

from domain.enums import IssueCategory, Severity, cap_linguistic_severity
from schemas.base import ApiModel
from schemas.issues import BoundingBox


class LinguisticFinding(ApiModel):
    """Normalized finding emitted by spelling, grammar, duplicate, or ambiguity analyzers."""

    type: str
    message: str
    severity: Severity = Severity.LOW
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    original_text: str
    suggestion: str | None = None
    location: BoundingBox
    original_location: BoundingBox | None = None
    rule_id: str | None = None
    category: IssueCategory = IssueCategory.LINGUISTIC

    @field_validator("severity", mode="before")
    @classmethod
    def cap_severity(cls, value: Severity | str) -> Severity:
        """Spellcheck, grammar, and dictionary findings cannot outrank MINOR."""
        return cap_linguistic_severity(value)


class SpellcheckAnalysis(ApiModel):
    """Output artifact of the typo/spelling analysis stage."""

    schema_version: str = "1.0"
    rule_version: str = "spellcheck/1.0.0"
    findings: list[LinguisticFinding] = Field(default_factory=list)


class GrammarAnalysis(ApiModel):
    """Output artifact of the grammar and style analysis stage."""

    schema_version: str = "1.0"
    rule_version: str = "grammar/1.0.0"
    findings: list[LinguisticFinding] = Field(default_factory=list)


class DuplicateAnalysis(ApiModel):
    """Output artifact of the duplicate content analysis stage."""

    schema_version: str = "1.0"
    rule_version: str = "duplicate/1.0.0"
    findings: list[LinguisticFinding] = Field(default_factory=list)


class AmbiguityAnalysis(ApiModel):
    """Output artifact of the contextual ambiguity and passive voice analysis stage."""

    schema_version: str = "1.0"
    rule_version: str = "ambiguity/1.0.0"
    findings: list[LinguisticFinding] = Field(default_factory=list)
