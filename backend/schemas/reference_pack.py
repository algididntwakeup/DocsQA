"""Schemas for Reference Packs, Rules, Benchmarks, and Evaluation Results."""

from __future__ import annotations

from typing import Literal

from domain.enums import Severity
from schemas.base import ApiModel

RuleKind = Literal["range", "unit", "numeric_limit", "terminology", "required_reference"]
ComparisonOperator = Literal["GE", "LE", "GT", "LT", "EQ"]
PackStatus = Literal["CONFIGURED", "UNCONFIGURED"]
ComplianceStatus = Literal["NON_COMPLIANT", "UNRESOLVED", "COMPLIANT"]


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


class BenchmarkCase(ApiModel):
    """Single benchmark verification fixture with expected rule triggers."""

    case_id: str
    name: str
    description: str
    document_text: str
    expected_triggers: list[str] = []
    is_negative_control: bool = False


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
