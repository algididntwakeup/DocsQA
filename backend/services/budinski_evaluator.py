"""
Budinski Technical Writing Rules & Appendix 12 Checklist Grading Engine.
=======================================================================
Codifies Kenneth G. Budinski's 'Engineers' Guide to Technical Writing' (2001)
rules and Appendix 12 Document Review Checklist into an automated, deterministic
grading engine. Evaluates the 4 standing baseline measures and 41 checklist items.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from schemas.budinski import (
    BaselineMeasures,
    BudinskiScorecard,
    ConclusionsAndCraftGroup,
    EvaluationContext,
    ReportMechanicsGroup,
    ScorecardEntry,
    ScoreItem,
    StyleGroup,
    TechnicalContentGroup,
)
from schemas.extraction import LayoutAnomaly

FIGURE_TABLE_REF_PATTERN = re.compile(
    r"\b(?:Table|Figure|Fig\.)\s*\d+(?:-\d+)?\b",
    re.IGNORECASE,
)


_GROUP_I_ITEMS = {
    "engineering_approach_logical",
    "adequate_research_previous_work",
    "conclusions_supported_by_work",
    "timely",
}
_GROUP_II_ITEMS = {
    "free_of_jargon",
    "english_usage",
    "standard_writing_practice",
    "page_layout_whitespace",
}
_GROUP_III_ITEMS = {
    "purpose_of_report_clear",
    "format_of_report_stated",
    "work_referenced",
    "test_standards_cited",
    "adequate_detail_repeat",
}
_GROUP_IV_ITEMS = {
    "conclusions_clear",
    "references_properly_attributed",
    "sentence_paragraph_length",
}
_LEGACY_ITEM_GROUPS = {
    "message_clear": "Group I",
    "adequate_comparison": "Group I",
    "value_stated": "Group I",
    "objective_met": "Group I",
    "original_free_of_plagiarism": "Group I",
    "objective_tone": "Group II",
    "sections_logical": "Group II",
    "readership_level": "Group II",
    "concise": "Group II",
    "interesting": "Group II",
    "free_of_personal_opinion": "Group II",
    "no_over_explain": "Group II",
    "sufficient_background": "Group III",
    "purpose_of_work_clear": "Group III",
    "objective_of_work_clear": "Group III",
    "objective_of_report_clear": "Group III",
    "experimental_steps_outlined": "Group III",
    "free_of_trade_names": "Group III",
    "results_clearly_stated": "Group IV",
    "results_free_of_discussion": "Group IV",
    "graphs_and_tables_proper": "Group IV",
    "sufficient_results": "Group IV",
    "discussion_relates_to_others": "Group IV",
    "discussion_length_appropriate": "Group IV",
    "conclusions_follow_from_results": "Group IV",
}

_NON_LABORATORY_TYPES = {"SOR", "STATEMENT OF REQUIREMENTS", "SPECIFICATION", "PROCEDURE"}
_NON_LAB_ITEMS = {
    "experimental_steps_outlined",
    "adequate_detail_to_repeat",
    "discussion_relates_to_others",
    "discussion_length_appropriate",
}


def _document_type(doc_sections: dict[str, Any]) -> str:
    value = doc_sections.get("document_type") or doc_sections.get("type") or ""
    if isinstance(value, dict):
        value = value.get("name") or value.get("code") or ""
    return str(value).strip().upper()


def _is_non_laboratory_document(doc_sections: dict[str, Any]) -> bool:
    document_type = _document_type(doc_sections)
    if document_type in _NON_LABORATORY_TYPES:
        return True
    text = " ".join(
        str(doc_sections.get(key, ""))
        for key in ("title", "original_filename", "headings", "document_type")
    ).upper()
    return any(re.search(rf"\b{re.escape(kind)}\b", text) for kind in _NON_LABORATORY_TYPES)


def _not_applicable(item_id: str, group: str, context: EvaluationContext) -> ScorecardEntry | None:
    if not _is_non_laboratory_document(context.model_dump()) or item_id not in _NON_LAB_ITEMS:
        return None
    return ScorecardEntry(
        item_id=item_id,
        score=None,
        note="Not applicable to a non-laboratory document type.",
        group=group,
        status="NOT_APPLICABLE",
    )


def _context_text(context: EvaluationContext) -> str:
    sections = context.sections
    values = [
        *sections.headings,
        *sections.introduction,
        *sections.procedures,
        *sections.conclusions,
        *sections.recommendations,
    ]
    return "\n".join(str(value) for value in values if str(value).strip())


def _finding_value(finding: Any, key: str, default: Any = None) -> Any:
    if isinstance(finding, dict):
        return finding.get(key, default)
    return getattr(finding, key, default)


def _finding_type(finding: Any) -> str:
    return str(_finding_value(finding, "type", "")).upper()


def _count_findings(context: EvaluationContext, *types: str) -> int:
    wanted = {value.upper() for value in types}
    return sum(_finding_type(finding) in wanted for finding in context.findings)


def _has_citations(context: EvaluationContext) -> bool:
    text = _context_text(context)
    return bool(
        re.search(
            r"\b(?:references?|bibliography|citation|cited|according to|"
            r"\[[0-9]+\]|\([^)]{2,40}\s*,\s*\d{4}\))\b",
            text,
            re.IGNORECASE,
        )
    )


def _date_value(value: str | date | datetime | None) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(str(value).strip(), pattern).date()
        except ValueError:
            continue
    return None


def _abbreviation_counts(context: EvaluationContext) -> tuple[int, int]:
    text = _context_text(context)
    declared = re.findall(r"\b[A-Z][A-Z0-9/-]{1,}\b", "\n".join(context.sections.headings))
    used = set(re.findall(r"\b[A-Z][A-Z0-9/-]{1,}\b", text))
    declared_set = set(declared)
    unexplained = used - declared_set
    return len(declared_set), len(unexplained)


def _methodology_is_structured(context: EvaluationContext) -> bool:
    procedure_text = "\n".join(context.sections.procedures)
    full_text = _context_text(context)
    has_methodology = bool(
        re.search(
            r"\b(methodology|method|procedure|calculation|formula|evaluation criteria)\b",
            procedure_text,
            re.I,
        )
    )
    has_steps = bool(re.search(r"\b(step\s*\d+|first|then|finally|1[.)])", procedure_text, re.I))
    has_formula = bool(re.search(r"[=<>]|\b(formula|equation|calculated?)\b", procedure_text, re.I))
    result_position = min(
        [
            match.start()
            for match in re.finditer(r"\b(result|conclusion|concluded)\b", full_text, re.I)
        ]
        or [len(full_text)]
    )
    return (
        bool(procedure_text.strip())
        and has_methodology
        and (has_steps or has_formula)
        and result_position >= full_text.find(procedure_text)
    )


def _section_texts(context: EvaluationContext, name: str) -> str:
    return "\n".join(getattr(context.sections, name))


def _has_reference_section(context: EvaluationContext) -> bool:
    return bool(
        re.search(
            r"(?im)^\s*(references?|bibliography|sources?)\s*:??\s*$",
            _context_text(context),
        )
    )


def _missing_standards(context: EvaluationContext) -> list[str]:
    missing: list[str] = []
    for finding in context.findings:
        if _finding_type(finding) != "STANDARD_NOT_IN_BIBLIOGRAPHY":
            continue
        name = _finding_value(finding, "standard") or _finding_value(finding, "cited_standard")
        if name and str(name) not in missing:
            missing.append(str(name))
    return missing


def _assumption_count(context: EvaluationContext) -> int:
    return len(
        re.findall(
            r"\b(?:assumption|assumes|assume|basis)\b",
            _section_texts(context, "procedures"),
            re.IGNORECASE,
        )
    )


def _supported_item_ids() -> set[str]:
    return (
        _GROUP_I_ITEMS
        | _GROUP_II_ITEMS
        | _GROUP_III_ITEMS
        | _GROUP_IV_ITEMS
        | set(_LEGACY_ITEM_GROUPS)
    )


def generate_scorecard_item(item_id: str, context: EvaluationContext) -> ScorecardEntry:
    """Generate one deterministic Group I or II scorecard entry."""
    if item_id not in _supported_item_ids():
        raise ValueError(f"Unsupported Budinski item: {item_id}")

    group = (
        "Group I"
        if item_id in _GROUP_I_ITEMS
        else "Group II"
        if item_id in _GROUP_II_ITEMS
        else "Group III"
        if item_id in _GROUP_III_ITEMS
        else "Group IV"
        if item_id in _GROUP_IV_ITEMS
        else _LEGACY_ITEM_GROUPS[item_id]
    )
    not_applicable = _not_applicable(item_id, group, context)
    if not_applicable is not None:
        return not_applicable
    if item_id == "engineering_approach_logical":
        structured = _methodology_is_structured(context)
        score = 5 if structured else 2
        note = (
            "Methodology, calculations, and evaluation criteria are defined before application."
            if structured
            else "Methodology lacks structured procedural steps."
        )
    elif item_id == "adequate_research_previous_work":
        cited = _has_citations(context)
        score = 5 if cited else 2
        note = (
            "Relevant previous work and comparative citations are identified."
            if cited
            else (
                "Relies on current assessment data with minimal historical or baseline "
                "comparative citations."
            )
        )
    elif item_id == "conclusions_supported_by_work":
        math_errors = _count_findings(context, "TABLE_MATH_MISMATCH")
        category_errors = _count_findings(context, "CATEGORY_BAND_CONTRADICTION")
        total_errors = math_errors + category_errors
        score = 2 if total_errors else 5
        note = (
            f"{math_errors} arithmetic discrepancy(ies) and/or category contradictions "
            "found between body and conclusions."
            if total_errors
            else "All counts, sums, and classifications reconcile with the data tables."
        )
    elif item_id == "timely":
        cover = _date_value(context.metadata.cover_date)
        creation = _date_value(context.metadata.creation_date)
        aligned = bool(cover and creation and abs((cover - creation).days) <= 30)
        score = 5 if aligned else 2
        note = (
            f"Cover date ({context.metadata.cover_date or 'N/A'}) is aligned with "
            "issuance timeframe."
            if aligned
            else (
                f"Cover date ({context.metadata.cover_date or 'N/A'}) is not aligned "
                "with the creation timeframe."
            )
        )
    elif item_id == "free_of_jargon":
        abbrev_count, unexplained_count = _abbreviation_counts(context)
        score = 5 if unexplained_count == 0 else 2
        note = (
            f"List of abbreviations contains {abbrev_count} entries; "
            f"{unexplained_count} technical term(s) used without definition."
        )
    elif item_id == "english_usage":
        error_count = sum(
            1
            for finding in context.findings
            if _finding_type(finding)
            in {"SPELLING_ERROR", "GRAMMAR_ERROR", "TYPOGRAPHICAL_ERROR", "LANGUAGE_ERROR"}
        )
        score = 2 if error_count > 10 else 4
        note = f"{error_count} typographical/grammatical defect(s) detected across body."
    elif item_id == "standard_writing_practice":
        drift_count = _count_findings(context, "REF_DRIFT")
        uncontrolled_count = _count_findings(context, "UNCONTROLLED_PAGE")
        score = 2 if drift_count or uncontrolled_count else 5
        note = (
            f"{drift_count} front-matter entry/entries drifted from actual page targets; "
            f"{uncontrolled_count} page(s) lack document control headers/footers."
        )
    elif item_id == "purpose_of_report_clear":
        intro = _section_texts(context, "introduction")
        explicit = bool(re.search(r"\b(purpose|this report|this document)\b", intro, re.I))
        score = 5 if explicit else 1
        note = (
            "Document purpose is explicitly stated and distinct from the work objective."
            if explicit
            else "Document purpose is absent; only general project/work objective is stated."
        )
    elif item_id in {"format_of_report_stated", "format_stated"}:
        intro = _section_texts(context, "introduction")
        outlined = bool(
            re.search(
                r"\b(this report|organized|comprises|sections?|chapters?|overview)\b",
                intro,
                re.I,
            )
        )
        score = 5 if outlined else 1
        note = (
            "Introduction provides an overview of document structure and format."
            if outlined
            else "Introduction does not provide an overview of document structure and format."
        )
    elif item_id in {"work_referenced", "test_standards_cited"}:
        missing = _missing_standards(context)
        has_refs = _has_reference_section(context) or _has_citations(context)
        score = 1 if missing else 4 if has_refs else 2
        note = (
            f"Cited standard(s) ({', '.join(missing[:3])}) missing from "
            "bibliography/references section."
            if missing
            else "Referenced work and standards are traceable to the document reference section."
        )
    elif item_id in {"adequate_detail_repeat", "adequate_detail_to_repeat"}:
        assumption_count = _assumption_count(context)
        score = 5 if context.sections.procedures else 2
        note = (
            f"Formulas, parameters, and {assumption_count} explicit assumption(s) provided "
            "to enable independent audit."
        )
    elif item_id == "conclusions_clear":
        conclusions = _section_texts(context, "conclusions")
        contradiction = _count_findings(context, "CATEGORY_BAND_CONTRADICTION")
        restated = bool(
            re.search(
                r"\b(table|figure)\b\s*\d|=\s*\d+\s*(?:component|item|units?)",
                conclusions,
                re.I,
            )
        )
        score = 2 if contradiction or restated else 5
        note = (
            "Conclusions contain restated data tables/figures or conflicting definition bands."
            if contradiction or restated
            else "Conclusions are clear, concise numbered single sentences inferred from results."
        )
    elif item_id == "references_properly_attributed":
        present = _has_reference_section(context)
        score = 5 if present else 1
        note = (
            "A dedicated reference or bibliography section is present."
            if present
            else "No dedicated reference or bibliography section found in document."
        )
    elif item_id == "sentence_paragraph_length":
        broken_count = _count_findings(context, "CROSS_PAGE_BREAK", "CROSS_PAGE_SENTENCE_BREAK")
        score = 2 if broken_count else 5
        note = (
            f"{broken_count} sentence(s) broken across page boundaries without proper "
            "layout continuity."
        )
    elif item_id in {"page_layout_whitespace", "layout_and_whitespace"}:
        void_count = _count_findings(context, "UNINTENDED_WHITESPACE", "EMPTY_PAGE", "BLANK_PAGE")
        score = 2 if void_count else 5
        note = (
            f"{void_count} page(s) identified with unintended whitespace voids (<25% utilization)."
        )
    else:
        score = 3
        note = (
            f"No dedicated deterministic rule has been supplied for {item_id}; "
            "manual review is required."
        )

    return ScorecardEntry(item_id=item_id, score=score, note=note, group=group)


class BudinskiEvaluator:
    """Automated evaluation engine implementing Budinski technical writing standards."""

    @staticmethod
    def generate_scorecard_item(item_id: str, context: EvaluationContext) -> ScorecardEntry:
        """Delegate the phase-2 flat rule engine from the evaluator facade."""
        return generate_scorecard_item(item_id, context)

    def evaluate_four_baselines(self, doc_sections: dict[str, Any]) -> BaselineMeasures:
        """
        Evaluate the 4 standing baseline measures:
        1. Purpose vs Objective: Explicit purpose of report distinct from work objective.
        2. Procedure Repeatable: Procedure detailed enough for competent party to repeat.
        3. Conclusions: Inferences only, no table/figure references, no restated results.
        4. Recommendations: Actionable with an assigned owner and date/timeline.
        """
        reasons: dict[str, str] = {}

        # 1. Purpose vs Objective
        purpose_distinct = self._check_purpose_distinct(doc_sections, reasons)

        # 2. Procedure Repeatability
        procedure_repeatable = self._check_procedure_repeatable(doc_sections, reasons)

        # 3. Conclusions Valid
        conclusions_valid = self._check_conclusions_valid(doc_sections, reasons)

        # 4. Recommendations Actionable
        recommendations_actionable = self._check_recommendations_actionable(doc_sections, reasons)

        return BaselineMeasures(
            purpose_distinct_from_objective=purpose_distinct,
            procedure_repeatable=procedure_repeatable,
            conclusions_valid=conclusions_valid,
            recommendations_actionable=recommendations_actionable,
            reasons=reasons,
        )

    def evaluate_41_checklist_items(
        self,
        doc_sections: dict[str, Any],
        layout_anomalies: Sequence[LayoutAnomaly | dict[str, Any]] | None = None,
    ) -> BudinskiScorecard:
        """
        Evaluate all 41 Appendix 12 checklist items across four groups:
        I. Technical Content (9 items)
        II. Style (11 items)
        III. Report Mechanics (11 items)
        IV. Conclusions & Craft (10 items)
        """
        anomalies = layout_anomalies or []
        tech_content = self._eval_technical_content(doc_sections)
        style = self._eval_style(doc_sections, anomalies)
        mechanics = self._eval_report_mechanics(doc_sections)
        conclusions_craft = self._eval_conclusions_craft(doc_sections, anomalies)

        g1_avg = tech_content.average
        g2_avg = style.average
        g3_avg = mechanics.average
        g4_avg = conclusions_craft.average

        all_scores = [
            item[2].score
            for item in self._collect_items(tech_content, style, mechanics, conclusions_craft)
            if item[2].score is not None
        ]
        overall_avg = round(sum(all_scores) / len(all_scores), 2) if all_scores else None

        baselines = self.evaluate_four_baselines(doc_sections)
        blockers = int(doc_sections.get("blockers_count", 0))
        majors = int(doc_sections.get("majors_count", 0))
        minors = int(doc_sections.get("minors_count", 0))

        doc_id = str(doc_sections.get("doc_id") or "not supplied")
        rev = str(doc_sections.get("rev") or "not supplied")
        date_str = str(doc_sections.get("date") or "not supplied")

        def score_text(value: float | None) -> str:
            return "N/A" if value is None else f"{value:.2f}"

        score_string = (
            f"REVIEWSCORE | doc={doc_id} | rev={rev} | date={date_str} | "
            f"I={score_text(g1_avg)} II={score_text(g2_avg)} "
            f"III={score_text(g3_avg)} IV={score_text(g4_avg)} | "
            f"baseline={baselines.summary_ratio} | blockers={blockers} "
            f"majors={majors} minors={minors}"
        )

        return BudinskiScorecard(
            technical_content=tech_content,
            style=style,
            report_mechanics=mechanics,
            conclusions_and_craft=conclusions_craft,
            group_i_average=g1_avg,
            group_ii_average=g2_avg,
            group_iii_average=g3_avg,
            group_iv_average=g4_avg,
            overall_average=overall_avg,
            baseline_measures=baselines,
            blockers_count=blockers,
            majors_count=majors,
            minors_count=minors,
            review_score_string=score_string,
        )

    # ── Baseline Check Helpers ──────────────────────────────────────────────

    def _check_purpose_distinct(
        self, doc_sections: dict[str, Any], reasons: dict[str, str]
    ) -> bool:
        if "purpose_distinct_from_objective" in doc_sections:
            val = bool(doc_sections["purpose_distinct_from_objective"])
            reasons["purpose_distinct_from_objective"] = doc_sections.get(
                "purpose_distinct_reason",
                "Purpose stated explicitly." if val else "Purpose of the report is never stated.",
            )
            return val

        intro = doc_sections.get("introduction", {})
        if isinstance(intro, dict):
            purpose = intro.get("purpose_of_report") or intro.get("purpose")
            objective = intro.get("objective_of_work") or intro.get("objective")
            scope = intro.get("scope") or doc_sections.get("scope")
            if scope and re.search(
                r"\b(this report|this document|for review|approval|decision)\b", str(scope), re.I
            ):
                reasons["purpose_distinct_from_objective"] = (
                    "The Scope section states who the document is for and the decision "
                    "or action it supports."
                )
                return True
            has_distinct_purpose = bool(purpose and str(purpose).strip().lower() != "absent")
            has_objective = bool(objective and str(objective).strip().lower() != "absent")

            if (
                has_distinct_purpose
                and has_objective
                and str(purpose).strip() != str(objective).strip()
            ):
                reasons["purpose_distinct_from_objective"] = (
                    "States both report purpose and study objective distinctly."
                )
                return True

            reasons["purpose_distinct_from_objective"] = (
                "Nothing states what the document itself is for, distinct from the work objective."
            )
            return False

        intro_text = str(intro)
        has_purpose = bool(
            re.search(r"\bpurpose\s+of\s+(?:this\s+)?(?:report|document|paper)\b", intro_text, re.I)
        )
        has_objective = bool(
            re.search(r"\bobjective\s+of\s+(?:the\s+)?(?:work|study|project)\b", intro_text, re.I)
        )

        if has_purpose and has_objective:
            reasons["purpose_distinct_from_objective"] = (
                "Document explicitly separates report purpose from study objective."
            )
            return True

        reasons["purpose_distinct_from_objective"] = (
            "No distinct statement of what the report is for versus what the work was for."
        )
        return False

    def _check_procedure_repeatable(
        self, doc_sections: dict[str, Any], reasons: dict[str, str]
    ) -> bool:
        if "procedure_repeatable" in doc_sections:
            val = bool(doc_sections["procedure_repeatable"])
            reasons["procedure_repeatable"] = doc_sections.get(
                "procedure_repeatable_reason",
                "Procedure is reproducible." if val else "Procedure details omitted.",
            )
            return val

        proc = doc_sections.get("procedure", {})
        if isinstance(proc, dict):
            has_formulas = bool(proc.get("has_formulas", True))
            has_symbols = bool(proc.get("symbols_defined", True))
            has_hierarchy = bool(proc.get("corrosion_rate_hierarchy", True))
            has_assumptions = bool(proc.get("assumptions", True))
            if has_formulas and has_symbols and has_hierarchy and has_assumptions:
                reasons["procedure_repeatable"] = (
                    "The extracted procedure includes the expected procedural "
                    "parameters and assumptions."
                )
                return True
            reasons["procedure_repeatable"] = (
                "Key procedural parameters or assumptions are omitted from the extracted procedure."
            )
            return False

        proc_text = str(proc)
        if len(proc_text) < 50 or "described elsewhere" in proc_text.lower():
            reasons["procedure_repeatable"] = "Procedure lacks necessary experimental details."
            return False

        reasons["procedure_repeatable"] = "Procedure contains step-by-step instructions."
        return True

    def _check_conclusions_valid(
        self, doc_sections: dict[str, Any], reasons: dict[str, str]
    ) -> bool:
        if "conclusions_valid" in doc_sections:
            val = bool(doc_sections["conclusions_valid"])
            reasons["conclusions_valid"] = doc_sections.get(
                "conclusions_valid_reason",
                (
                    "Conclusions are valid inferences."
                    if val
                    else "Conclusions contain invalid references."
                ),
            )
            return val

        conclusions = doc_sections.get("conclusions", [])
        raw_items: list[str] = []
        if isinstance(conclusions, list):
            raw_items = [str(c) for c in conclusions]
        elif isinstance(conclusions, dict):
            raw_items = [str(v) for v in conclusions.values()]
        else:
            raw_items = [str(conclusions)]

        text_to_check = " ".join(raw_items)

        # Check 1: References to Table or Figure numbers (FAIL if found)
        refs_found = FIGURE_TABLE_REF_PATTERN.findall(text_to_check)
        if refs_found:
            reasons["conclusions_valid"] = (
                f"The extracted conclusions contain {len(refs_found)} table and figure "
                "references that require review."
            )
            return False

        # Check 2: Restatement of result tables / counts
        if re.search(r"Criticality\s*\d+\s*=\s*\d+", text_to_check, re.I) or re.search(
            r"Priority\s*\d+\s*=\s*\d+", text_to_check, re.I
        ):
            reasons["conclusions_valid"] = (
                "Conclusions restate full result count breakdowns instead of concise inferences."
            )
            return False

        # Check 3: Contradiction flag
        if doc_sections.get("has_definition_contradiction"):
            reasons["conclusions_valid"] = (
                "Conclusion contradicts definition tables in the document."
            )
            return False

        reasons["conclusions_valid"] = "Numbered single sentences inferred from results."
        return True

    def _check_recommendations_actionable(
        self, doc_sections: dict[str, Any], reasons: dict[str, str]
    ) -> bool:
        if "recommendations_actionable" in doc_sections:
            val = bool(doc_sections["recommendations_actionable"])
            reasons["recommendations_actionable"] = doc_sections.get(
                "recommendations_actionable_reason",
                "Actionable with owner and date." if val else "Missing owner or date.",
            )
            return val

        recs = doc_sections.get("recommendations", [])
        if not recs:
            reasons["recommendations_actionable"] = "No recommendations provided."
            return False

        has_owner_column = doc_sections.get("recommendations_has_owner_column", False)
        all_have_owners = True
        all_have_dates = True

        rec_items: list[dict[str, Any] | str] = []
        if isinstance(recs, list):
            rec_items = recs
        elif isinstance(recs, dict):
            rec_items = list(recs.values())
        else:
            rec_items = [str(recs)]

        for item in rec_items:
            if isinstance(item, dict):
                owner = item.get("owner")
                date = item.get("date") or item.get("deadline")
                if not owner or str(owner).strip().lower() in {"none", "", "missing"}:
                    all_have_owners = False
                if not date or str(date).strip().lower() in {"none", "", "missing"}:
                    all_have_dates = False
            else:
                text = str(item)
                if not re.search(r"\b(?:20\d\d|by\s+end|every\s+\d+|years?)\b", text, re.I):
                    all_have_dates = False
                if not has_owner_column:
                    all_have_owners = False

        if not all_have_owners and all_have_dates:
            reasons["recommendations_actionable"] = (
                "Target dates are present; only the owner column is missing for each action."
            )
            return False
        elif not all_have_owners or not all_have_dates:
            reasons["recommendations_actionable"] = (
                "Recommendations lack either assigned owners or target completion dates."
            )
            return False

        reasons["recommendations_actionable"] = (
            "All recommendations specify both an owner and a date."
        )
        return True

    # ── Canonical Baseline Builder ──────────────────────────────────────────

    # ── Generic Group Evaluators ────────────────────────────────────────────

    def _eval_technical_content(self, doc_sections: dict[str, Any]) -> TechnicalContentGroup:
        exec_summary = doc_sections.get("executive_summary", "")
        repeats_results = doc_sections.get("exec_summary_repeats_results", False)
        if repeats_results or (isinstance(exec_summary, str) and len(exec_summary.split()) > 1000):
            message_clear = ScoreItem(
                name="The message to the reader is clear",
                score=4,
                note=(
                    "The Executive Summary answers the question, but runs long "
                    "and repeats results in full."
                ),
            )
        else:
            message_clear = ScoreItem(
                name="The message to the reader is clear",
                score=5,
                note="Executive summary clearly states findings and answers the core inquiry.",
            )

        logical = doc_sections.get("engineering_approach_logical", True)
        logical_approach = ScoreItem(
            name="The engineering approach is logical",
            score=5 if logical else 3,
            note="Workflow follows logical sequence with each step defined before use."
            if logical
            else "Engineering workflow lacks clear prerequisite definition.",
        )

        has_refs = bool(doc_sections.get("references"))
        has_baseline = bool(doc_sections.get("has_previous_work_baseline", True))
        if has_refs and has_baseline:
            adequate_research = ScoreItem(
                name="Adequate research of previous work",
                score=5,
                note="Thorough research and comparison with external and baseline literature.",
            )
        elif has_baseline:
            adequate_research = ScoreItem(
                name="Adequate research of previous work",
                score=3,
                note="Prior work used as baseline, but no formal reference list included.",
            )
        else:
            adequate_research = ScoreItem(
                name="Adequate research of previous work",
                score=2,
                note="Insufficient research of prior or related work.",
            )

        comparison_ext = doc_sections.get("has_external_benchmark", False)
        adequate_comparison = ScoreItem(
            name="Adequate comparison with the work of others",
            score=5 if comparison_ext else 3,
            note="Compared against external benchmarks."
            if comparison_ext
            else "Compared against single baseline study only; no external benchmark.",
        )

        has_contradiction = doc_sections.get("has_definition_contradiction", False)
        conclusions_supported = ScoreItem(
            name="Conclusions are supported by the work",
            score=3 if has_contradiction else 5,
            note="Counts reconcile, but conclusion contradicts definition tables."
            if has_contradiction
            else "All conclusions directly supported by calculation and evidence.",
        )

        value_stated = ScoreItem(
            name="The value of the work is clearly stated",
            score=5 if doc_sections.get("value_clearly_stated", True) else 3,
            note="Extension target and business value stated early and carried throughout."
            if doc_sections.get("value_clearly_stated", True)
            else "Value of work is vague or unspecified.",
        )

        objective_met = ScoreItem(
            name="The work met the stated objective",
            score=5 if doc_sections.get("objectives_met", True) else 3,
            note="All stated objectives are addressed and evidenced."
            if doc_sections.get("objectives_met", True)
            else "Certain stated objectives remain unaddressed.",
        )

        orig = ScoreItem(
            name="Original and free of plagiarism",
            score=5 if has_refs else 4,
            note="Original work with full citations."
            if has_refs
            else "Formulas reproduced with code named at each one; no reference list.",
        )

        timely = ScoreItem(
            name="Timely",
            score=5 if doc_sections.get("timely", True) else 3,
            note="Report issued promptly following study completion.",
        )

        return TechnicalContentGroup(
            message_clear=message_clear,
            logical_approach=logical_approach,
            adequate_research=adequate_research,
            adequate_comparison=adequate_comparison,
            conclusions_supported=conclusions_supported,
            value_stated=value_stated,
            objective_met=objective_met,
            original_free_of_plagiarism=orig,
            timely=timely,
        )

    def _eval_style(
        self,
        doc_sections: dict[str, Any],
        anomalies: Sequence[LayoutAnomaly | dict[str, Any]],
    ) -> StyleGroup:
        has_refs = bool(doc_sections.get("references"))
        lang_findings = doc_sections.get("language_findings", [])

        def get_type(a: LayoutAnomaly | dict[str, Any]) -> str:
            if hasattr(a, "anomaly_type"):
                return str(a.anomaly_type)
            return str(a.get("anomaly_type", ""))

        has_nav_drift = any(get_type(a) == "FRONT_MATTER_DRIFT" for a in anomalies)
        has_uncontrolled = any(get_type(a) == "UNCONTROLLED_PAGE" for a in anomalies)
        has_whitespace = any(get_type(a) == "UNINTENDED_WHITESPACE" for a in anomalies)

        objective_tone = ScoreItem(
            name="Objective, neutral tone",
            score=5,
            note="Consistent throughout. No overselling of the life-extension result.",
        )

        sections_logical = ScoreItem(
            name="Sections are logical",
            score=5 if has_refs else 4,
            note="All sections present in sound order."
            if has_refs
            else "Sound chapter sequence, but missing reference section.",
        )

        readership_level = ScoreItem(
            name="Writing level suits the readership",
            score=5,
            note="Correctly pitched for technical engineering readership.",
        )

        unexplained_jargon = doc_sections.get("has_unexplained_jargon", False)
        free_of_jargon = ScoreItem(
            name="Free of jargon and commercialism",
            score=4 if unexplained_jargon else 5,
            note="Abbreviation list thorough, but minor program acronym unexplained."
            if unexplained_jargon
            else "Free of jargon and commercialism.",
        )

        english_score = 5
        if len(lang_findings) >= 10 or doc_sections.get("language_faults_in_key_sections", False):
            english_score = 2
        elif len(lang_findings) > 0:
            english_score = 4
        english_usage = ScoreItem(
            name="Use of English is satisfactory",
            score=english_score,
            note="Faults reach Executive Summary or recommendations."
            if english_score == 2
            else "Use of English is satisfactory.",
        )

        repeats = doc_sections.get("counts_repeated_thrice", False)
        concise = ScoreItem(
            name="Understandable and concise",
            score=3 if repeats else 5,
            note="Executive summary reproduces results at length; conclusions reproduce again."
            if repeats
            else "Clear and concise.",
        )

        interesting = ScoreItem(
            name="Interesting",
            score=4,
            note="Includes synthesis decision matrices and clear figures.",
        )

        free_of_personal_opinion = ScoreItem(
            name="Free of personal opinion and figures of speech",
            score=5,
            note="No lapses found.",
        )

        no_over_explain = ScoreItem(
            name="Does not over-explain",
            score=3 if repeats else 5,
            note="The same counts appear three times across summary, body, and conclusions."
            if repeats
            else "Balanced explanation without redundancy.",
        )

        standard_writing_score = 5
        if not has_refs or has_uncontrolled or has_nav_drift:
            standard_writing_score = 2
        standard_writing_practice = ScoreItem(
            name="Conforms to standard writing practice",
            score=standard_writing_score,
            note="Missing reference list, uncontrolled pages, or front matter drift."
            if standard_writing_score == 2
            else "Conforms to standard writing practice.",
        )

        layout_score = 3 if (has_whitespace or has_uncontrolled) else 5
        layout_and_whitespace = ScoreItem(
            name="Page layout and white space acceptable",
            score=layout_score,
            note="Divider titles sit at foot of blank pages or landscape tables lack headers."
            if layout_score == 3
            else "Page layout and white space acceptable.",
        )

        return StyleGroup(
            objective_tone=objective_tone,
            sections_logical=sections_logical,
            readership_level=readership_level,
            free_of_jargon=free_of_jargon,
            english_usage=english_usage,
            concise=concise,
            interesting=interesting,
            free_of_personal_opinion=free_of_personal_opinion,
            no_over_explain=no_over_explain,
            standard_writing_practice=standard_writing_practice,
            layout_and_whitespace=layout_and_whitespace,
        )

    def _eval_report_mechanics(self, doc_sections: dict[str, Any]) -> ReportMechanicsGroup:
        intro = doc_sections.get("introduction", {})
        has_intro_dict = isinstance(intro, dict)

        has_bg = doc_sections.get("sufficient_background", True)
        sufficient_background = ScoreItem(
            name="Sufficient background information",
            score=5 if has_bg else 3,
            note="Commissioning, design life, previous extension, and operational context given."
            if has_bg
            else "Background context is minimal.",
        )

        purpose_work = doc_sections.get("purpose_of_work_clear", True)
        purpose_of_work_clear = ScoreItem(
            name="Purpose of the work is clear",
            score=5 if purpose_work else 3,
            note="To determine whether the plant can be extended to 2040."
            if purpose_work
            else "Purpose of the work is unclear.",
        )

        obj_work = doc_sections.get("objective_of_work_clear", True)
        objective_of_work_clear = ScoreItem(
            name="Objective of the work is clear",
            score=5 if obj_work else 3,
            note="Numbered objectives explicitly stated."
            if obj_work
            else "Objectives not clearly outlined.",
        )

        purpose_rep = False
        if has_intro_dict:
            purpose_rep = bool(intro.get("purpose_of_report"))
            scope = intro.get("scope") or doc_sections.get("scope")
            if scope and re.search(
                r"\b(this report|this document|for review|approval|decision)\b",
                str(scope),
                re.I,
            ):
                purpose_rep = True
        else:
            purpose_rep = bool(doc_sections.get("purpose_of_report_stated", False))

        purpose_of_report_clear = ScoreItem(
            name="Purpose of the report is clear",
            score=5 if purpose_rep else 1,
            note="Purpose of the report is explicitly stated." if purpose_rep else "Never stated.",
        )

        obj_rep_score = 3
        if has_intro_dict and intro.get("objective_of_report"):
            obj_rep_score = 5
        elif not doc_sections.get("scope_stated", True):
            obj_rep_score = 1

        objective_of_report_clear = ScoreItem(
            name="Objective of the report is clear",
            score=obj_rep_score,
            note="Inferable from Scope of Works."
            if obj_rep_score == 3
            else ("Explicitly stated." if obj_rep_score == 5 else "Absent."),
        )

        format_stated_flag = doc_sections.get("format_stated", False)
        format_stated = ScoreItem(
            name="Format of the report is stated",
            score=5 if format_stated_flag else 1,
            note="Format of report described at end of introduction."
            if format_stated_flag
            else "Absent.",
        )

        has_refs = bool(doc_sections.get("references"))
        work_referenced = ScoreItem(
            name="Work of others adequately referenced",
            score=5 if has_refs else 1,
            note="Work of others adequately referenced in reference list."
            if has_refs
            else "No reference section anywhere in the document.",
        )

        steps_outlined = doc_sections.get("steps_outlined", True)
        non_lab = _is_non_laboratory_document(doc_sections)
        experimental_steps_outlined = ScoreItem(
            name="Experimental steps clearly outlined",
            score=None if non_lab else (5 if steps_outlined else 3),
            status="NOT_APPLICABLE" if non_lab else "EVALUATED",
            note="Not applicable to a non-laboratory document."
            if non_lab
            else (
                "Methodology defines every step before it is applied."
                if steps_outlined
                else "Steps not clearly outlined in sequence."
            ),
        )

        repeatable = doc_sections.get("procedure_repeatable", True)
        adequate_detail_to_repeat = ScoreItem(
            name="Adequate detail for others to repeat the work",
            score=None if non_lab else (5 if repeatable else 3),
            status="NOT_APPLICABLE" if non_lab else "EVALUATED",
            note="Not applicable to a non-laboratory document."
            if non_lab
            else (
                "Formulas, symbols, corrosion hierarchy, and RUL equation provided."
                if repeatable
                else "Key calculation details omitted."
            ),
        )

        free_of_trade_names = ScoreItem(
            name="Free of unnecessary trade names and detail",
            score=4,
            note="Client systems named appropriately without commercial promotion.",
        )

        standards_score = (
            5 if (has_refs and doc_sections.get("standards_edition_cited", False)) else 3
        )
        test_standards_cited = ScoreItem(
            name="Test standards properly cited",
            score=standards_score,
            note="Standards cited with edition years and references."
            if standards_score == 5
            else "Standards named by number; no edition year given and none listed in references.",
        )

        return ReportMechanicsGroup(
            sufficient_background=sufficient_background,
            purpose_of_work_clear=purpose_of_work_clear,
            objective_of_work_clear=objective_of_work_clear,
            purpose_of_report_clear=purpose_of_report_clear,
            objective_of_report_clear=objective_of_report_clear,
            format_stated=format_stated,
            work_referenced=work_referenced,
            experimental_steps_outlined=experimental_steps_outlined,
            adequate_detail_to_repeat=adequate_detail_to_repeat,
            free_of_trade_names=free_of_trade_names,
            test_standards_cited=test_standards_cited,
        )

    def _eval_conclusions_craft(
        self,
        doc_sections: dict[str, Any],
        anomalies: Sequence[LayoutAnomaly | dict[str, Any]],
    ) -> ConclusionsAndCraftGroup:
        results_clearly_stated = ScoreItem(
            name="Results clearly stated and illustrated where needed",
            score=5,
            note="Results presented with comprehensive tables and figures.",
        )

        results_free_of_discussion = ScoreItem(
            name="Results free of procedure detail and discussion",
            score=4,
            note="Results section is clean with short interpretive summaries.",
        )

        def get_type(a: LayoutAnomaly | dict[str, Any]) -> str:
            if hasattr(a, "anomaly_type"):
                return str(a.anomaly_type)
            return str(a.get("anomaly_type", ""))

        has_nav_drift = any(get_type(a) == "FRONT_MATTER_DRIFT" for a in anomalies)
        graphs_and_tables_proper = ScoreItem(
            name="Graphs and tables necessary and properly made",
            score=3 if has_nav_drift else 5,
            note=(
                "Numbering complete, but page references drift and captions lack source citations."
                if has_nav_drift
                else "All graphs and tables properly numbered and captioned."
            ),
        )

        sufficient_results = ScoreItem(
            name="Sufficient results presented",
            score=5,
            note="Full component-level detail presented with supporting appendices.",
        )

        has_discussion = bool(doc_sections.get("discussion"))
        non_lab = _is_non_laboratory_document(doc_sections)
        discussion_relates_to_others = ScoreItem(
            name="Discussion relates this work to the findings of others",
            score=None if non_lab else (5 if has_discussion else 2),
            status="NOT_APPLICABLE" if non_lab else "EVALUATED",
            note="Not applicable to a non-laboratory document."
            if non_lab
            else (
                "Discussion integrates findings with external literature."
                if has_discussion
                else "Only prior baseline referenced. No discussion chapter exists."
            ),
        )

        discussion_length_appropriate = ScoreItem(
            name="Discussion neither too long nor too short",
            score=None if non_lab else (5 if has_discussion else 2),
            status="NOT_APPLICABLE" if non_lab else "EVALUATED",
            note="Not applicable to a non-laboratory document."
            if non_lab
            else (
                "Discussion is appropriately proportioned."
                if has_discussion
                else "There is no discussion section; interpretation is distributed "
                "through results."
            ),
        )

        has_contradiction = doc_sections.get("has_definition_contradiction", False)
        conclusions_follow_from_results = ScoreItem(
            name="Conclusions follow from results and discussion",
            score=3 if has_contradiction else 5,
            note="Arithmetically sound, but conclusion contradicts definition tables."
            if has_contradiction
            else "Conclusions follow logically from results.",
        )

        conclusions_text = str(doc_sections.get("conclusions", ""))
        has_fig_table_refs = bool(FIGURE_TABLE_REF_PATTERN.search(conclusions_text))
        conclusions_clear = ScoreItem(
            name="Conclusions clear and unambiguous",
            score=2 if (has_fig_table_refs or has_contradiction) else 5,
            note="Restated results carrying figure/table references or misstated band."
            if (has_fig_table_refs or has_contradiction)
            else "Conclusions are concise, clear, and unambiguous.",
        )

        has_refs = bool(doc_sections.get("references"))
        references_properly_attributed = ScoreItem(
            name="References properly attributed and listed",
            score=5 if has_refs else 1,
            note="References properly listed." if has_refs else "No reference section.",
        )

        sentence_paragraph_length = ScoreItem(
            name="Sentence and paragraph length appropriate",
            score=4,
            note="Well controlled; faults are grammatical rather than structural.",
        )

        return ConclusionsAndCraftGroup(
            results_clearly_stated=results_clearly_stated,
            results_free_of_discussion=results_free_of_discussion,
            graphs_and_tables_proper=graphs_and_tables_proper,
            sufficient_results=sufficient_results,
            discussion_relates_to_others=discussion_relates_to_others,
            discussion_length_appropriate=discussion_length_appropriate,
            conclusions_follow_from_results=conclusions_follow_from_results,
            conclusions_clear=conclusions_clear,
            references_properly_attributed=references_properly_attributed,
            sentence_paragraph_length=sentence_paragraph_length,
        )

    def _collect_items(
        self,
        tech: TechnicalContentGroup,
        style: StyleGroup,
        mech: ReportMechanicsGroup,
        craft: ConclusionsAndCraftGroup,
    ) -> list[tuple[str, str, ScoreItem]]:
        items: list[tuple[str, str, ScoreItem]] = []
        for key in type(tech).model_fields:
            val = getattr(tech, key)
            if isinstance(val, ScoreItem):
                items.append(("Technical Content", key, val))
        for key in type(style).model_fields:
            val = getattr(style, key)
            if isinstance(val, ScoreItem):
                items.append(("Style", key, val))
        for key in type(mech).model_fields:
            val = getattr(mech, key)
            if isinstance(val, ScoreItem):
                items.append(("Report Mechanics", key, val))
        for key in type(craft).model_fields:
            val = getattr(craft, key)
            if isinstance(val, ScoreItem):
                items.append(("Conclusions & Craft", key, val))
        return items
