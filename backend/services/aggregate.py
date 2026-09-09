"""Issue Aggregation Service.

Normalizes all linguistic, traceability, and system stage findings into
the unified Issue schema with deterministic severity mapping, deduplication,
and versioned audit evidence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from domain.enums import IssueCategory, Severity, cap_linguistic_severity
from schemas.base import ApiModel
from schemas.extraction import CoordinateContract
from schemas.issues import (
    BoundingBox,
    IssueEvidence,
    IssueRead,
    LinguisticEvidence,
    ReferenceDriftEvidence,
    ReferenceRuleEvidence,
    RevisionEvidence,
    StageFailureEvidence,
    StandardEvidence,
    TableMathEvidence,
)
from schemas.linguistic import (
    AmbiguityAnalysis,
    DuplicateAnalysis,
    GrammarAnalysis,
    LinguisticFinding,
    SpellcheckAnalysis,
)
from schemas.ref_drift import RefDriftAnalysis, RefDriftFinding
from schemas.reference_pack import ReferenceFinding
from schemas.revision import RevisionAnalysis, RevisionSourceName
from schemas.standard_traceability import StandardFinding, StandardTraceabilityAnalysis
from schemas.table_math import TableMathAnalysis, TableMathFinding

AGGREGATION_SCHEMA_VERSION = "1.0"
AGGREGATION_RULE_VERSION = "aggregation/1.0.0"


def to_bounding_box(coord: CoordinateContract | None, default_page: int = 0) -> BoundingBox:
    """Safely convert a CoordinateContract to a BoundingBox with fallback dimensions."""
    if coord is None:
        return BoundingBox(
            page_index=default_page,
            x0=0.0,
            y0=0.0,
            x1=0.0,
            y1=0.0,
            page_width=612.0,
            page_height=792.0,
        )
    return BoundingBox(
        page_index=coord.page_index,
        x0=max(0.0, coord.x0),
        y0=max(0.0, coord.y0),
        x1=max(0.0, coord.x1),
        y1=max(0.0, coord.y1),
        page_width=coord.page_width if coord.page_width > 0 else 612.0,
        page_height=coord.page_height if coord.page_height > 0 else 792.0,
    )


class AggregationResult(ApiModel):
    """Unified artifact containing aggregated and deduplicated document findings."""

    schema_version: str = AGGREGATION_SCHEMA_VERSION
    rule_version: str = AGGREGATION_RULE_VERSION
    document_id: UUID
    total_issues: int
    issues_by_category: dict[str, int]
    issues_by_severity: dict[str, int]
    issues: list[IssueRead]


def _normalize_revision(
    document_id: UUID,
    revision: RevisionAnalysis,
    now: datetime,
) -> list[IssueRead]:
    """Normalize revision sync analysis into canonical Issue records."""
    if revision.outcome != "MISMATCH":
        return []

    sources_map: dict[RevisionSourceName, str | None] = {
        s.source: s.normalized_value for s in revision.sources
    }
    locations = [to_bounding_box(s.location) for s in revision.sources if s.location is not None]

    evidence = RevisionEvidence(
        extractor_version="1.0",
        rule_version=revision.rule_version,
        filename_revision=sources_map.get("FILENAME"),
        cover_revision=sources_map.get("COVER"),
        revision_sheet_revision=sources_map.get("REVISION_SHEET"),
        sources_disagreeing=revision.sources_disagreeing,
        locations=locations,
    )

    issue = IssueRead(
        id=uuid4(),
        document_id=document_id,
        category=IssueCategory.TRACEABILITY,
        type="REVISION_MISMATCH",
        severity=Severity.CRITICAL,
        confidence=1.0,
        message=(
            f"Revision mismatch detected across sources: {', '.join(revision.sources_disagreeing)} "
            f"(filename: {sources_map.get('FILENAME') or 'None'}, "
            f"cover: {sources_map.get('COVER') or 'None'}, "
            f"revision table: {sources_map.get('REVISION_SHEET') or 'None'})"
        ),
        evidence=evidence,
        version=1,
        created_at=now,
        updated_at=now,
    )
    return [issue]


def _normalize_table_math_finding(
    document_id: UUID,
    finding: TableMathFinding,
    rule_version: str,
    now: datetime,
) -> IssueRead:
    """Normalize one table math finding to an Issue with TableMathEvidence."""
    severity_map = {
        "TABLE_MATH_MISMATCH": Severity.CRITICAL,
        "TOTAL_NOT_FOUND": Severity.HIGH,
        "UNIT_MISMATCH": Severity.HIGH,
        "MALFORMED_TABLE_ROW": Severity.MEDIUM,
    }
    confidence_map = {
        "TABLE_MATH_MISMATCH": 1.0,
        "TOTAL_NOT_FOUND": 0.9,
        "UNIT_MISMATCH": 1.0,
        "MALFORMED_TABLE_ROW": 0.8,
    }

    severity = severity_map.get(finding.kind, Severity.HIGH)
    confidence = confidence_map.get(finding.kind, 1.0)

    total_loc = to_bounding_box(finding.total_location)
    operand_locs = [to_bounding_box(loc) for loc in finding.operand_locations]

    computed = finding.computed_value if finding.computed_value is not None else Decimal("0")
    stated = finding.stated_value if finding.stated_value is not None else Decimal("0")
    delta = finding.delta if finding.delta is not None else Decimal("0")
    tolerance = finding.tolerance if finding.tolerance is not None else Decimal("0")

    evidence = TableMathEvidence(
        extractor_version="1.0",
        rule_version=rule_version,
        computed_value=computed,
        stated_value=stated,
        delta=delta,
        tolerance=tolerance,
        total_location=total_loc,
        operand_locations=operand_locs,
    )

    return IssueRead(
        id=uuid4(),
        document_id=document_id,
        category=IssueCategory.TRACEABILITY,
        type=finding.kind,
        severity=severity,
        confidence=confidence,
        message=finding.message,
        evidence=evidence,
        version=1,
        created_at=now,
        updated_at=now,
    )


def _normalize_ref_drift_finding(
    document_id: UUID,
    finding: RefDriftFinding,
    rule_version: str,
    now: datetime,
) -> IssueRead:
    """Normalize one reference drift finding to an Issue with ReferenceDriftEvidence."""
    severity_map = {
        "REF_DRIFT": Severity.HIGH,
        "MISSING_TARGET": Severity.HIGH,
        "DUPLICATE_CAPTION": Severity.MEDIUM,
    }
    confidence_map = {
        "REF_DRIFT": 1.0,
        "MISSING_TARGET": 1.0,
        "DUPLICATE_CAPTION": 0.8,
    }

    severity = severity_map.get(finding.kind, Severity.HIGH)
    confidence = confidence_map.get(finding.kind, 1.0)

    entry_loc = to_bounding_box(finding.entry_location)
    target_loc = (
        to_bounding_box(finding.target_location)
        if finding.target_location is not None
        else entry_loc
    )

    evidence = ReferenceDriftEvidence(
        extractor_version="1.0",
        rule_version=rule_version,
        label=finding.label,
        referenced_page_label=finding.referenced_page_label,
        actual_page_label=(
            finding.actual_page_label if finding.actual_page_label is not None else "NOT_FOUND"
        ),
        page_delta=finding.page_delta if finding.page_delta is not None else 0,
        entry_location=entry_loc,
        target_location=target_loc,
    )

    return IssueRead(
        id=uuid4(),
        document_id=document_id,
        category=IssueCategory.TRACEABILITY,
        type=finding.kind,
        severity=severity,
        confidence=confidence,
        message=finding.message,
        evidence=evidence,
        version=1,
        created_at=now,
        updated_at=now,
    )


def _normalize_standard_finding(
    document_id: UUID,
    finding: StandardFinding,
    rule_version: str,
    now: datetime,
) -> IssueRead:
    """Normalize one standard traceability finding to an Issue with StandardEvidence."""
    severity_map = {
        "STANDARD_NOT_IN_BIBLIOGRAPHY": Severity.HIGH,
        "EDITION_YEAR_MISMATCH": Severity.HIGH,
        "AMBIGUOUS_STANDARD": Severity.LOW,
    }
    confidence_map = {
        "STANDARD_NOT_IN_BIBLIOGRAPHY": 1.0,
        "EDITION_YEAR_MISMATCH": 1.0,
        "AMBIGUOUS_STANDARD": 0.5,
    }

    severity = severity_map.get(finding.kind, Severity.HIGH)
    confidence = confidence_map.get(finding.kind, 1.0)

    body_loc = to_bounding_box(finding.body_location)
    bib_loc = (
        to_bounding_box(finding.bibliography_location)
        if finding.bibliography_location is not None
        else None
    )

    evidence = StandardEvidence(
        extractor_version="1.0",
        rule_version=rule_version,
        cited_standard=finding.cited_standard,
        body_edition_year=finding.body_edition_year,
        bibliography_entry=finding.bibliography_entry,
        bibliography_edition_year=finding.bibliography_edition_year,
        body_location=body_loc,
        bibliography_location=bib_loc,
    )

    messages = {
        "STANDARD_NOT_IN_BIBLIOGRAPHY": (
            f"Cited standard '{finding.cited_standard}' is missing from the "
            "references / bibliography section."
        ),
        "EDITION_YEAR_MISMATCH": (
            f"Standard '{finding.cited_standard}' cited with edition "
            f"{finding.body_edition_year}, but bibliography specifies edition "
            f"{finding.bibliography_edition_year}."
        ),
        "AMBIGUOUS_STANDARD": (
            f"Standard citation '{finding.cited_standard}' is ambiguous and "
            "requires human verification."
        ),
    }

    return IssueRead(
        id=uuid4(),
        document_id=document_id,
        category=IssueCategory.TRACEABILITY,
        type=finding.kind,
        severity=severity,
        confidence=confidence,
        message=messages.get(finding.kind, f"Standard finding: {finding.cited_standard}"),
        evidence=evidence,
        version=1,
        created_at=now,
        updated_at=now,
    )


def _normalize_stage_failure(
    document_id: UUID,
    stage_name: str,
    error_code: str,
    retryable: bool,
    now: datetime,
) -> IssueRead:
    """Generate a synthetic diagnostic issue for a failed analyzer stage."""
    evidence = StageFailureEvidence(
        extractor_version="1.0",
        rule_version="pipeline/1.0.0",
        stage=stage_name,
        error_code=error_code,
        retryable=retryable,
    )

    return IssueRead(
        id=uuid4(),
        document_id=document_id,
        category=IssueCategory.SYSTEM,
        type="STAGE_FAILURE",
        severity=Severity.HIGH,
        confidence=1.0,
        message=f"Analyzer stage '{stage_name}' failed execution: {error_code}",
        evidence=evidence,
        version=1,
        created_at=now,
        updated_at=now,
    )


def _normalize_linguistic_finding(
    document_id: UUID,
    finding: LinguisticFinding,
    rule_version: str,
    now: datetime,
) -> IssueRead:
    """Normalize one linguistic finding (spelling, grammar, duplicate, ambiguity) to an Issue."""
    evidence = LinguisticEvidence(
        extractor_version="1.0",
        rule_version=rule_version,
        original_text=finding.original_text,
        suggestion=finding.suggestion,
        location=finding.location,
        original_location=finding.original_location,
    )

    return IssueRead(
        id=uuid4(),
        document_id=document_id,
        category=IssueCategory.LINGUISTIC,
        type=finding.type,
        severity=cap_linguistic_severity(finding.severity),
        confidence=finding.confidence,
        message=finding.message,
        evidence=evidence,
        version=1,
        created_at=now,
        updated_at=now,
    )


def normalize_reference_findings(
    document_id: UUID,
    findings: list[ReferenceFinding],
    now: datetime | None = None,
) -> list[IssueRead]:
    """Normalize reference pack rule findings into canonical Issue records."""
    if now is None:
        now = datetime.now(UTC)

    issues: list[IssueRead] = []
    for f in findings:
        loc = BoundingBox(
            page_index=max(0, f.page_number - 1),
            x0=0.0,
            y0=0.0,
            x1=612.0,
            y1=792.0,
            page_width=612.0,
            page_height=792.0,
        )
        evidence = ReferenceRuleEvidence(
            extractor_version="1.0",
            rule_version=f"{f.standard}:{f.edition}",
            standard=f.standard,
            edition=f.edition,
            clause=f.clause,
            standard_page=f.standard_page,
            rule_kind=f.rule_kind,
            detected_parameter=f.detected_parameter,
            detected_value=f.detected_value,
            compliance_status=f.compliance_status,
            location=loc,
        )
        issues.append(
            IssueRead(
                id=uuid4(),
                document_id=document_id,
                category=IssueCategory.TRACEABILITY,
                type=f.rule_id,
                severity=f.severity,
                confidence=1.0,
                message=f.message,
                evidence=evidence,
                included_in_report=True,
                reviewer_note=None,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
    return issues


def _dedup_key(issue: IssueRead) -> tuple[Any, ...]:
    """Compute an identity tuple for cross-finding deduplication."""
    ev: IssueEvidence = issue.evidence
    if isinstance(ev, RevisionEvidence):
        return (issue.category, issue.type, tuple(sorted(ev.sources_disagreeing)))
    if isinstance(ev, TableMathEvidence):
        return (
            issue.category,
            issue.type,
            ev.total_location.page_index,
            round(ev.total_location.x0, 1),
            round(ev.total_location.y0, 1),
            str(ev.stated_value),
            str(ev.computed_value),
        )
    if isinstance(ev, ReferenceDriftEvidence):
        return (
            issue.category,
            issue.type,
            ev.label,
            ev.referenced_page_label,
            ev.actual_page_label,
            ev.entry_location.page_index,
        )
    if isinstance(ev, StandardEvidence):
        return (
            issue.category,
            issue.type,
            ev.cited_standard,
            ev.body_location.page_index,
            round(ev.body_location.y0, 1),
        )
    if isinstance(ev, ReferenceRuleEvidence):
        return (
            issue.category,
            issue.type,
            ev.standard,
            ev.clause,
            ev.location.page_index,
            ev.detected_parameter or "",
            ev.detected_value or "",
        )
    if isinstance(ev, LinguisticEvidence):
        if isinstance(ev.location, BoundingBox):
            loc_key = (
                ev.location.page_index,
                round(ev.location.x0, 1),
                round(ev.location.y0, 1),
            )
        else:
            loc_key = (
                ev.location.page_index,
                float(ev.location.start),
                float(ev.location.end),
            )
        return (
            issue.category,
            issue.type,
            ev.original_text.lower(),
            *loc_key,
        )
    if isinstance(ev, StageFailureEvidence):
        return (issue.category, issue.type, ev.stage)
    return (issue.category, issue.type, issue.message)


def aggregate_document_findings(
    document_id: UUID,
    revision: RevisionAnalysis | None = None,
    table_math: TableMathAnalysis | None = None,
    ref_drift: RefDriftAnalysis | None = None,
    standard_traceability: StandardTraceabilityAnalysis | None = None,
    spellcheck: SpellcheckAnalysis | None = None,
    grammar: GrammarAnalysis | None = None,
    duplicate: DuplicateAnalysis | None = None,
    ambiguity: AmbiguityAnalysis | None = None,
    failed_stages: list[tuple[str, str, bool]] | None = None,
    reference_findings: list[ReferenceFinding] | None = None,
) -> AggregationResult:
    """Aggregate, normalize, and deduplicate findings across all pipeline stages."""
    now = datetime.now(UTC)
    raw_candidates: list[IssueRead] = []

    # 1. Revision sync
    if revision is not None:
        raw_candidates.extend(_normalize_revision(document_id, revision, now))

    # 2. Table math
    if table_math is not None:
        for tm_finding in table_math.findings:
            raw_candidates.append(
                _normalize_table_math_finding(document_id, tm_finding, table_math.rule_version, now)
            )

    # 3. Reference drift
    if ref_drift is not None:
        for rd_finding in ref_drift.findings:
            raw_candidates.append(
                _normalize_ref_drift_finding(document_id, rd_finding, ref_drift.rule_version, now)
            )

    # 4. Standard traceability
    if standard_traceability is not None:
        for std_finding in standard_traceability.findings:
            raw_candidates.append(
                _normalize_standard_finding(
                    document_id, std_finding, standard_traceability.rule_version, now
                )
            )

    # 5. Linguistic analyzers (M4)
    if spellcheck is not None:
        for sc_finding in spellcheck.findings:
            raw_candidates.append(
                _normalize_linguistic_finding(document_id, sc_finding, spellcheck.rule_version, now)
            )

    if grammar is not None:
        for gm_finding in grammar.findings:
            raw_candidates.append(
                _normalize_linguistic_finding(document_id, gm_finding, grammar.rule_version, now)
            )

    if duplicate is not None:
        for dp_finding in duplicate.findings:
            raw_candidates.append(
                _normalize_linguistic_finding(document_id, dp_finding, duplicate.rule_version, now)
            )

    if ambiguity is not None:
        for am_finding in ambiguity.findings:
            raw_candidates.append(
                _normalize_linguistic_finding(document_id, am_finding, ambiguity.rule_version, now)
            )

    # 6. Reference pack standard findings
    if reference_findings:
        raw_candidates.extend(normalize_reference_findings(document_id, reference_findings, now))

    # 7. Failed stages
    if failed_stages:
        for stage_name, error_code, retryable in failed_stages:
            raw_candidates.append(
                _normalize_stage_failure(document_id, stage_name, error_code, retryable, now)
            )

    # Deduplicate while preserving order
    seen_keys: set[tuple[Any, ...]] = set()
    deduped_issues: list[IssueRead] = []
    for candidate in raw_candidates:
        key = _dedup_key(candidate)
        if key not in seen_keys:
            seen_keys.add(key)
            deduped_issues.append(candidate)

    # Compute metrics
    issues_by_cat: dict[str, int] = {cat.value: 0 for cat in IssueCategory}
    issues_by_sev: dict[str, int] = {sev.value: 0 for sev in Severity}

    for issue in deduped_issues:
        issues_by_cat[issue.category.value] = issues_by_cat.get(issue.category.value, 0) + 1
        issues_by_sev[issue.severity.value] = issues_by_sev.get(issue.severity.value, 0) + 1

    return AggregationResult(
        document_id=document_id,
        total_issues=len(deduped_issues),
        issues_by_category=issues_by_cat,
        issues_by_severity=issues_by_sev,
        issues=deduped_issues,
    )
