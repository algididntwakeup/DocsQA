"""Schemas for Reference Packs, Rules, Benchmarks, and Evaluation Results."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, model_validator

from domain.enums import EvaluationStatus, Severity
from schemas.base import ApiModel
from schemas.issues import BoundingBox

RuleKind = Literal["range", "unit", "numeric_limit", "terminology", "required_reference"]
ComparisonOperator = Literal["GE", "LE", "GT", "LT", "EQ"]
PackStatus = Literal["CONFIGURED", "UNCONFIGURED"]
ComplianceStatus = Literal["NON_COMPLIANT", "UNRESOLVED", "COMPLIANT"]


class PackOrigin(StrEnum):
    """Where a reference pack came from: shipped with the system or uploaded by a tenant."""

    SYSTEM = "SYSTEM"
    CUSTOM = "CUSTOM"


class PackScope(StrEnum):
    """Visibility of a reference pack: a single project or the whole tenant."""

    PROJECT_ONLY = "PROJECT_ONLY"
    GLOBAL_TENANT = "GLOBAL_TENANT"


class RuleEvaluationStatus(StrEnum):
    """Deterministic outcome of evaluating one pack rule against extracted facts."""

    PASS = "PASS"
    FINDING = "FINDING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNRESOLVED = "UNRESOLVED"


class RuleEvaluationResult(ApiModel):
    """Outcome of evaluating a single RuleDefinition against extracted document facts."""

    pack_id: str
    rule_id: str
    standard_code: str
    edition: str
    clause: str
    source_page: int = Field(ge=1)
    detected_fact: str | None = None
    expected_condition: str
    evidence_coordinates: list[BoundingBox] = []
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    status: RuleEvaluationStatus


class RuleSeverity(StrEnum):
    """Rule severity labels used inside reference pack rule definitions."""

    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    RECOMMENDATION = "RECOMMENDATION"


class RuleType(StrEnum):
    """Deterministic check kinds supported by pack rule definitions."""

    REQUIRED_CITATION = "required_citation"
    CITATION_EDITION_MATCH = "citation_edition_match"
    REQUIRED_SECTION_FIELD = "required_section_field"
    NUMERIC_RANGE = "numeric_range"
    UNIT_COMPATIBILITY = "unit_compatibility"
    TERMINOLOGY_CONSISTENCY = "terminology_consistency"
    TABLE_PROSE_RECONCILIATION = "table_prose_reconciliation"
    APPLICABILITY_CONDITION = "applicability_condition"


class RangeParameters(ApiModel):
    """Parameters for numeric range boundaries."""

    parameter_name: str
    pattern: str
    min_value: float | None = None
    max_value: float | None = None
    inclusive_min: bool = True
    inclusive_max: bool = True
    allowed_units: list[str] = []


class UnitParameters(ApiModel):
    """Parameters for unit validity and consistency."""

    parameter_name: str
    pattern: str
    canonical_unit: str
    allowed_units: list[str]
    forbidden_units: list[str] = []


class NumericLimitParameters(ApiModel):
    """Parameters for threshold and ratio limit checks."""

    parameter_name: str
    pattern: str
    operator: ComparisonOperator
    limit_value: float
    tolerance: float = 0.0
    context_pattern: str | None = None


class TerminologyParameters(ApiModel):
    """Parameters for standard technical terminology governance."""

    term: str
    preferred_term: str
    deprecated_terms: list[str]
    context_keywords: list[str] = []


class RequiredReferenceParameters(ApiModel):
    """Parameters for mandatory citations triggered by document contents."""

    trigger_keywords: list[str]
    required_standard: str
    required_clause: str | None = None
    exemption_keywords: list[str] = []


class ReferenceRule(ApiModel):
    """A governed engineering rule derived from an official reference standard."""

    rule_id: str
    standard: str
    edition: str
    clause: str
    standard_page: int
    title: str
    severity: Severity
    kind: RuleKind
    range_params: RangeParameters | None = None
    unit_params: UnitParameters | None = None
    numeric_limit_params: NumericLimitParameters | None = None
    terminology_params: TerminologyParameters | None = None
    required_reference_params: RequiredReferenceParameters | None = None
    message_template: str
    recommendation_template: str
    requires_engineering_judgement: bool = False
    default_status: ComplianceStatus = "NON_COMPLIANT"


class ReferencePackManifest(ApiModel):
    """Metadata describing a published reference standard pack."""

    pack_id: str
    standard_code: str
    standard_name: str
    edition: str
    authority: str
    version: str
    description: str
    status: PackStatus = "CONFIGURED"
    source_pdf: str | None = None
    source_available: bool = False
    rules_count: int = 0
    benchmarks_count: int = 0


class PackManifest(ApiModel):
    """Metadata for a built-in (SYSTEM) or user-uploaded (CUSTOM) reference pack."""

    pack_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,63}$")
    name: str = Field(min_length=1, max_length=200)
    standard_code: str = Field(min_length=1, max_length=100)
    edition_year: str = Field(pattern=r"^\d{4}$|^\d{4}-\d{2}$")
    origin: PackOrigin = PackOrigin.SYSTEM
    scope: PackScope = PackScope.GLOBAL_TENANT
    version: str = Field(
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
    )
    status: PackStatus = "UNCONFIGURED"
    tenant_id: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def custom_packs_must_have_tenant(self) -> PackManifest:
        if self.origin is PackOrigin.CUSTOM and not self.tenant_id:
            raise ValueError("CUSTOM pack requires tenant_id")
        return self


class RuleDefinition(ApiModel):
    """A single deterministic rule declared in a pack's rules.yaml."""

    rule_id: str = Field(min_length=1, max_length=100)
    standard_code: str = Field(min_length=1, max_length=100)
    clause: str = Field(min_length=1, max_length=100)
    rule_type: RuleType
    severity: RuleSeverity
    parameters: dict[str, Any] = {}
    expected_condition: str = Field(min_length=1)
    recommendation_template: str = Field(min_length=1)


class PackBundleUpload(ApiModel):
    """Validated payload extracted from an uploaded reference pack zip bundle."""

    manifest: PackManifest
    rules: list[RuleDefinition] = []

    @model_validator(mode="after")
    def custom_bundle_constraints(self) -> PackBundleUpload:
        if self.manifest.origin is not PackOrigin.CUSTOM:
            raise ValueError("Uploaded bundles must declare origin=CUSTOM")
        rule_ids = [r.rule_id for r in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Duplicate rule_id in bundle")
        for rule in self.rules:
            if rule.standard_code != self.manifest.standard_code:
                raise ValueError(
                    f"Rule {rule.rule_id} standard_code does not match manifest"
                )
        return self


class BenchmarkCase(ApiModel):
    """Single benchmark verification fixture with expected rule triggers."""

    case_id: str
    name: str
    description: str
    document_text: str
    expected_triggers: list[str] = []
    is_negative_control: bool = False


class BenchmarkExpectation(ApiModel):
    """Expected deterministic evaluation outcome for a custom-pack benchmark case."""

    case_id: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    input_fact: dict[str, Any]
    expected_status: EvaluationStatus
    expected_rule_id: str | None = None


class BenchmarkCaseResult(ApiModel):
    """Outcome of evaluating one benchmark case against active rules."""

    case_id: str
    passed: bool
    expected_triggers: list[str]
    actual_triggers: list[str]
    true_positives: list[str]
    false_positives: list[str]
    false_negatives: list[str]


class BenchmarkEvaluationResult(ApiModel):
    """Aggregated precision, recall, and false-positive metrics across a benchmark suite."""

    standard_code: str
    edition: str
    total_cases: int
    total_rules: int
    tp_count: int
    fp_count: int
    tn_count: int
    fn_count: int
    precision: float
    recall: float
    false_positive_rate: float
    case_results: list[BenchmarkCaseResult]


class ReferenceFinding(ApiModel):
    """Finding emitted when a reference rule detects non-compliance."""

    rule_id: str
    standard: str
    edition: str
    clause: str
    standard_page: int
    rule_kind: RuleKind
    severity: Severity
    message: str
    recommendation: str
    detected_fact: str
    detected_parameter: str | None = None
    detected_value: str | None = None
    compliance_status: ComplianceStatus = "NON_COMPLIANT"
    page_number: int = 1
