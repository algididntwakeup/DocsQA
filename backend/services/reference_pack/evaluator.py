"""Deterministic rule evaluator for reference standards packs."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from schemas.reference_pack import (
    NumericLimitParameters,
    RangeParameters,
    ReferenceFinding,
    ReferenceRule,
    RequiredReferenceParameters,
    TerminologyParameters,
    UnitParameters,
)

if TYPE_CHECKING:
    from schemas.extraction import ExtractionArtifact


class ReferenceRuleEvaluator:
    """Evaluates reference rules against extracted text spans or raw text documents."""

    def __init__(self, rules: list[ReferenceRule]) -> None:
        self.rules = rules

    def evaluate_text(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[ReferenceFinding]:
        """Evaluate all active rules against raw document text."""
        findings: list[ReferenceFinding] = []
        for rule in self.rules:
            if rule.kind == "range" and rule.range_params:
                findings.extend(
                    self._eval_range(rule, rule.range_params, text, page_number)
                )
            elif rule.kind == "unit" and rule.unit_params:
                findings.extend(
                    self._eval_unit(rule, rule.unit_params, text, page_number)
                )
            elif rule.kind == "numeric_limit" and rule.numeric_limit_params:
                findings.extend(
                    self._eval_numeric_limit(rule, rule.numeric_limit_params, text, page_number)
                )
            elif rule.kind == "terminology" and rule.terminology_params:
                findings.extend(
                    self._eval_terminology(rule, rule.terminology_params, text, page_number)
                )
            elif rule.kind == "required_reference" and rule.required_reference_params:
                findings.extend(
                    self._eval_required_reference(
                        rule, rule.required_reference_params, text, page_number
                    )
                )
        return findings

    def evaluate_artifact(
        self,
        artifact: ExtractionArtifact,
    ) -> list[ReferenceFinding]:
        """Evaluate rules across an extracted PDF document artifact."""
        # Group text spans by page
        pages: dict[int, list[str]] = {}
        for span in artifact.spans:
            p = span.bbox.page_index + 1
            pages.setdefault(p, []).append(span.text)
        for heading in artifact.headings:
            p = heading.bbox.page_index + 1
            pages.setdefault(p, []).append(heading.text)

        all_findings: list[ReferenceFinding] = []
        full_text_combined = " ".join(" ".join(lines) for lines in pages.values())

        for p, lines in sorted(pages.items()):
            page_text = "\n".join(lines)
            # Evaluate range, unit, numeric_limit, and terminology per page
            for rule in self.rules:
                if rule.kind == "range" and rule.range_params:
                    all_findings.extend(
                        self._eval_range(rule, rule.range_params, page_text, p)
                    )
                elif rule.kind == "unit" and rule.unit_params:
                    all_findings.extend(
                        self._eval_unit(rule, rule.unit_params, page_text, p)
                    )
                elif rule.kind == "numeric_limit" and rule.numeric_limit_params:
                    all_findings.extend(
                        self._eval_numeric_limit(rule, rule.numeric_limit_params, page_text, p)
                    )
                elif rule.kind == "terminology" and rule.terminology_params:
                    all_findings.extend(
                        self._eval_terminology(rule, rule.terminology_params, page_text, p)
                    )

        # Evaluate required_reference across the entire document
        for rule in self.rules:
            if rule.kind == "required_reference" and rule.required_reference_params:
                all_findings.extend(
                    self._eval_required_reference(
                        rule, rule.required_reference_params, full_text_combined, 1
                    )
                )

        return self._deduplicate(all_findings)

    def _create_finding(
        self,
        rule: ReferenceRule,
        message: str,
        recommendation: str,
        detected_fact: str,
        detected_parameter: str | None,
        detected_value: str | None,
        page_number: int,
    ) -> ReferenceFinding:
        compliance_status = (
            "UNRESOLVED"
            if rule.requires_engineering_judgement
            else rule.default_status
        )
        return ReferenceFinding(
            rule_id=rule.rule_id,
            standard=rule.standard,
            edition=rule.edition,
            clause=rule.clause,
            standard_page=rule.standard_page,
            rule_kind=rule.kind,
            severity=rule.severity,
            message=message,
            recommendation=recommendation,
            detected_fact=detected_fact,
            detected_parameter=detected_parameter,
            detected_value=detected_value,
            compliance_status=compliance_status,
            page_number=page_number,
        )

    # ── Rule Kind Evaluators ──────────────────────────────────────────

    def _eval_range(
        self,
        rule: ReferenceRule,
        params: RangeParameters,
        text: str,
        page_number: int,
    ) -> list[ReferenceFinding]:
        findings: list[ReferenceFinding] = []
        try:
            pattern = re.compile(params.pattern, re.IGNORECASE)
        except re.error:
            return []

        for match in pattern.finditer(text):
            val_str = match.group(1) if match.groups() else match.group(0)
            try:
                val = float(val_str.replace(",", ""))
            except ValueError:
                continue

            unit = match.group(2) if len(match.groups()) >= 2 else ""
            unit_suffix = f" {unit}".rstrip()

            violates = False
            if params.min_value is not None:
                violates_min = (
                    val < params.min_value if params.inclusive_min else val <= params.min_value
                )
                if violates_min:
                    violates = True

            if params.max_value is not None:
                violates_max = (
                    val > params.max_value if params.inclusive_max else val >= params.max_value
                )
                if violates_max:
                    violates = True

            if violates:
                min_repr = params.min_value if params.min_value is not None else "-∞"
                max_repr = params.max_value if params.max_value is not None else "+∞"
                fact = (
                    f"{params.parameter_name} of {val}{unit_suffix} is outside "
                    f"permitted standard range [{min_repr}, {max_repr}]."
                )
                msg = rule.message_template.format(
                    parameter=params.parameter_name,
                    value=val,
                    unit=unit,
                    clause=rule.clause,
                ) if "{" in rule.message_template else rule.message_template
                rec = rule.recommendation_template.format(
                    parameter=params.parameter_name,
                    min_val=params.min_value,
                    max_val=params.max_value,
                    clause=rule.clause,
                ) if "{" in rule.recommendation_template else rule.recommendation_template

                findings.append(
                    self._create_finding(
                        rule=rule,
                        message=msg,
                        recommendation=rec,
                        detected_fact=fact,
                        detected_parameter=params.parameter_name,
                        detected_value=str(val),
                        page_number=page_number,
                    )
                )
        return findings

    def _eval_unit(
        self,
        rule: ReferenceRule,
        params: UnitParameters,
        text: str,
        page_number: int,
    ) -> list[ReferenceFinding]:
        findings: list[ReferenceFinding] = []
        try:
            pattern = re.compile(params.pattern, re.IGNORECASE)
        except re.error:
            return []

        allowed_lower = {u.lower() for u in params.allowed_units}
        forbidden_lower = {u.lower() for u in params.forbidden_units}

        for match in pattern.finditer(text):
            detected_unit = match.group(1).strip() if match.groups() else ""
            if not detected_unit:
                continue

            detected_lower = detected_unit.lower()
            is_forbidden = detected_lower in forbidden_lower
            is_not_allowed = detected_lower not in allowed_lower

            if is_forbidden or is_not_allowed:
                fact = (
                    f"Non-standard or forbidden unit '{detected_unit}' used for "
                    f"{params.parameter_name}."
                )
                msg = rule.message_template.format(
                    parameter=params.parameter_name,
                    unit=detected_unit,
                    clause=rule.clause,
                ) if "{" in rule.message_template else rule.message_template
                rec = rule.recommendation_template.format(
                    parameter=params.parameter_name,
                    canonical=params.canonical_unit,
                    allowed=", ".join(params.allowed_units),
                    clause=rule.clause,
                ) if "{" in rule.recommendation_template else rule.recommendation_template

                findings.append(
                    self._create_finding(
                        rule=rule,
                        message=msg,
                        recommendation=rec,
                        detected_fact=fact,
                        detected_parameter=params.parameter_name,
                        detected_value=detected_unit,
                        page_number=page_number,
                    )
                )
        return findings

    def _eval_numeric_limit(
        self,
        rule: ReferenceRule,
        params: NumericLimitParameters,
        text: str,
        page_number: int,
    ) -> list[ReferenceFinding]:
        findings: list[ReferenceFinding] = []
        if params.context_pattern and not re.search(params.context_pattern, text, re.IGNORECASE):
            return []

        try:
            pattern = re.compile(params.pattern, re.IGNORECASE)
        except re.error:
            return []

        for match in pattern.finditer(text):
            val_str = match.group(1) if match.groups() else match.group(0)
            try:
                val = float(val_str.replace(",", ""))
            except ValueError:
                continue

            tol = params.tolerance
            lim = params.limit_value
            violates = False

            if params.operator == "GE":
                violates = val < (lim - tol)
            elif params.operator == "LE":
                violates = val > (lim + tol)
            elif params.operator == "GT":
                violates = val <= lim
            elif params.operator == "LT":
                violates = val >= lim
            elif params.operator == "EQ":
                violates = abs(val - lim) > tol

            if violates:
                fact = (
                    f"{params.parameter_name} value {val} violates standard limit "
                    f"({params.operator} {lim})."
                )
                msg = rule.message_template.format(
                    parameter=params.parameter_name,
                    value=val,
                    limit=lim,
                    clause=rule.clause,
                ) if "{" in rule.message_template else rule.message_template
                rec = rule.recommendation_template.format(
                    parameter=params.parameter_name,
                    limit=lim,
                    operator=params.operator,
                    clause=rule.clause,
                ) if "{" in rule.recommendation_template else rule.recommendation_template

                findings.append(
                    self._create_finding(
                        rule=rule,
                        message=msg,
                        recommendation=rec,
                        detected_fact=fact,
                        detected_parameter=params.parameter_name,
                        detected_value=str(val),
                        page_number=page_number,
                    )
                )
        return findings

    def _eval_terminology(
        self,
        rule: ReferenceRule,
        params: TerminologyParameters,
        text: str,
        page_number: int,
    ) -> list[ReferenceFinding]:
        findings: list[ReferenceFinding] = []
        for dep in params.deprecated_terms:
            pattern = re.compile(r"\b" + re.escape(dep) + r"\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                # Verify at least one keyword appears outside the deprecated term
                if params.context_keywords:
                    text_without_match = text[: match.start()] + " " + text[match.end() :]
                    found_context = any(
                        re.search(r"\b" + re.escape(kw) + r"\b", text_without_match, re.IGNORECASE)
                        for kw in params.context_keywords
                    )
                    if not found_context:
                        continue

                fact = (
                    f"Non-standard terminology '{match.group(0)}' used instead of governed "
                    f"term '{params.preferred_term}'."
                )
                msg = rule.message_template.format(
                    deprecated=match.group(0),
                    preferred=params.preferred_term,
                    clause=rule.clause,
                ) if "{" in rule.message_template else rule.message_template
                rec = rule.recommendation_template.format(
                    preferred=params.preferred_term,
                    clause=rule.clause,
                ) if "{" in rule.recommendation_template else rule.recommendation_template

                findings.append(
                    self._create_finding(
                        rule=rule,
                        message=msg,
                        recommendation=rec,
                        detected_fact=fact,
                        detected_parameter=params.term,
                        detected_value=match.group(0),
                        page_number=page_number,
                    )
                )
        return findings

    def _eval_required_reference(
        self,
        rule: ReferenceRule,
        params: RequiredReferenceParameters,
        text: str,
        page_number: int,
    ) -> list[ReferenceFinding]:
        findings: list[ReferenceFinding] = []
        triggered_keyword: str | None = None
        for kw in params.trigger_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE):
                triggered_keyword = kw
                break

        if not triggered_keyword:
            return []

        # Check for exemption keywords
        for ex in params.exemption_keywords:
            if re.search(r"\b" + re.escape(ex) + r"\b", text, re.IGNORECASE):
                return []

        # Check for presence of required standard / clause
        has_standard = bool(
            re.search(r"\b" + re.escape(params.required_standard) + r"\b", text, re.IGNORECASE)
        )
        has_clause = True
        if params.required_clause:
            has_clause = bool(
                re.search(r"\b" + re.escape(params.required_clause) + r"\b", text, re.IGNORECASE)
            )

        if not (has_standard and has_clause):
            fact = (
                f"Document specifies '{triggered_keyword}' without mandatory reference to "
                f"{params.required_standard}"
                + (f" clause {params.required_clause}" if params.required_clause else "")
                + "."
            )
            msg = rule.message_template.format(
                trigger=triggered_keyword,
                required_standard=params.required_standard,
                clause=rule.clause,
            ) if "{" in rule.message_template else rule.message_template
            rec = rule.recommendation_template.format(
                required_standard=params.required_standard,
                clause=rule.clause,
            ) if "{" in rule.recommendation_template else rule.recommendation_template

            findings.append(
                self._create_finding(
                    rule=rule,
                    message=msg,
                    recommendation=rec,
                    detected_fact=fact,
                    detected_parameter=triggered_keyword,
                    detected_value=None,
                    page_number=page_number,
                )
            )
        return findings

    @staticmethod
    def _deduplicate(findings: list[ReferenceFinding]) -> list[ReferenceFinding]:
        seen: set[tuple[str, str, int]] = set()
        unique: list[ReferenceFinding] = []
        for f in findings:
            key = (f.rule_id, f.detected_fact, f.page_number)
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique
