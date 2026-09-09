"""
Budinski Technical Writing Grading Schema Models (Appendix 12).
==============================================================
Defines strict Pydantic schemas for the 4 baseline measures and the 41
Appendix 12 review checklist items divided into 4 groups:
1. Technical Content (Does the document have substance?)
2. Style (Is it written appropriately for the application?)
3. Report Mechanics (Introduction and Procedure)
4. Conclusions & Craft (Results, Discussion, Conclusions and Craft)
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, computed_field

from schemas.base import ApiModel


class DocumentMetadata(ApiModel):
    """Document identity and date context used by the refactored evaluator."""

    title: str = ""
    doc_no: str = ""
    rev: str = ""
    cover_date: str | None = None
    creation_date: str | None = None
    page_count: int = Field(default=0, ge=0)


class ExtractedSections(ApiModel):
    """Normalized section text supplied to the evaluator."""

    headings: list[str] = Field(default_factory=list)
    introduction: list[str] = Field(default_factory=list)
    procedures: list[str] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class EvaluationContext(ApiModel):
    """All document context required by a deterministic Budinski evaluation."""

    metadata: DocumentMetadata
    sections: ExtractedSections
    findings: list[Any] = Field(default_factory=list)


class ScorecardEntry(ApiModel):
    """Flat scorecard item used by the phase-1 evaluator contract."""

    item_id: str
    score: int = Field(ge=1, le=5)
    note: str = ""
    group: str


class ScoreItem(ApiModel):
    """A single review checklist item with 1-5 score and reviewer note."""

    name: str = Field(default="", description="Name or title of checklist item.")
    score: int = Field(ge=1, le=5, description="Objective score from 1 (disagree) to 5 (agree).")
    note: str = Field(default="", description="Reviewer observation and justification.")


class TechnicalContentGroup(ApiModel):
    """Group I: Technical Content — Does the document have substance? (9 items)."""

    message_clear: ScoreItem = Field(description="The message to the reader is clear.")
    logical_approach: ScoreItem = Field(description="The engineering approach is logical.")
    adequate_research: ScoreItem = Field(description="Adequate research of previous work.")
    adequate_comparison: ScoreItem = Field(
        description="Adequate comparison with the work of others."
    )
    conclusions_supported: ScoreItem = Field(description="Conclusions are supported by the work.")
    value_stated: ScoreItem = Field(description="The value of the work is clearly stated.")
    objective_met: ScoreItem = Field(description="The work met the stated objective.")
    original_free_of_plagiarism: ScoreItem = Field(description="Original and free of plagiarism.")
    timely: ScoreItem = Field(description="Timely.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def average(self) -> float:
        scores = [
            self.message_clear.score,
            self.logical_approach.score,
            self.adequate_research.score,
            self.adequate_comparison.score,
            self.conclusions_supported.score,
            self.value_stated.score,
            self.objective_met.score,
            self.original_free_of_plagiarism.score,
            self.timely.score,
        ]
        return round(sum(scores) / len(scores), 2)


class StyleGroup(ApiModel):
    """Group II: Style — Is it written appropriately for the application? (11 items)."""

    objective_tone: ScoreItem = Field(description="Objective, neutral tone.")
    sections_logical: ScoreItem = Field(description="Sections are logical.")
    readership_level: ScoreItem = Field(description="Writing level suits the readership.")
    free_of_jargon: ScoreItem = Field(description="Free of jargon and commercialism.")
    english_usage: ScoreItem = Field(description="Use of English is satisfactory.")
    concise: ScoreItem = Field(description="Understandable and concise.")
    interesting: ScoreItem = Field(description="Interesting.")
    free_of_personal_opinion: ScoreItem = Field(
        description="Free of personal opinion and figures of speech."
    )
    no_over_explain: ScoreItem = Field(description="Does not over-explain.")
    standard_writing_practice: ScoreItem = Field(
        description="Conforms to standard writing practice."
    )
    layout_and_whitespace: ScoreItem = Field(
        description="Page layout and white space acceptable."
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def average(self) -> float:
        scores = [
            self.objective_tone.score,
            self.sections_logical.score,
            self.readership_level.score,
            self.free_of_jargon.score,
            self.english_usage.score,
            self.concise.score,
            self.interesting.score,
            self.free_of_personal_opinion.score,
            self.no_over_explain.score,
            self.standard_writing_practice.score,
            self.layout_and_whitespace.score,
        ]
        return round(sum(scores) / len(scores), 2)


class ReportMechanicsGroup(ApiModel):
    """Group III: Report Mechanics — Introduction and Procedure (11 items)."""

    # Introduction (7 items)
    sufficient_background: ScoreItem = Field(description="Sufficient background information.")
    purpose_of_work_clear: ScoreItem = Field(description="Purpose of the work is clear.")
    objective_of_work_clear: ScoreItem = Field(description="Objective of the work is clear.")
    purpose_of_report_clear: ScoreItem = Field(description="Purpose of the report is clear.")
    objective_of_report_clear: ScoreItem = Field(description="Objective of the report is clear.")
    format_stated: ScoreItem = Field(description="Format of the report is stated.")
    work_referenced: ScoreItem = Field(description="Work of others adequately referenced.")

    # Procedure (4 items)
    experimental_steps_outlined: ScoreItem = Field(
        description="Experimental steps clearly outlined."
    )
    adequate_detail_to_repeat: ScoreItem = Field(
        description="Adequate detail for others to repeat the work."
    )
    free_of_trade_names: ScoreItem = Field(
        description="Free of unnecessary trade names and detail."
    )
    test_standards_cited: ScoreItem = Field(description="Test standards properly cited.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def average(self) -> float:
        scores = [
            self.sufficient_background.score,
            self.purpose_of_work_clear.score,
            self.objective_of_work_clear.score,
            self.purpose_of_report_clear.score,
            self.objective_of_report_clear.score,
            self.format_stated.score,
            self.work_referenced.score,
            self.experimental_steps_outlined.score,
            self.adequate_detail_to_repeat.score,
            self.free_of_trade_names.score,
            self.test_standards_cited.score,
        ]
        return round(sum(scores) / len(scores), 2)


class ConclusionsAndCraftGroup(ApiModel):
    """Group IV: Results, Discussion, Conclusions and Craft (10 items)."""

    results_clearly_stated: ScoreItem = Field(
        description="Results clearly stated and illustrated where needed."
    )
    results_free_of_discussion: ScoreItem = Field(
        description="Results free of procedure detail and discussion."
    )
    graphs_and_tables_proper: ScoreItem = Field(
        description="Graphs and tables necessary and properly made."
    )
    sufficient_results: ScoreItem = Field(description="Sufficient results presented.")
    discussion_relates_to_others: ScoreItem = Field(
        description="Discussion relates this work to the findings of others."
    )
    discussion_length_appropriate: ScoreItem = Field(
        description="Discussion neither too long nor too short."
    )
    conclusions_follow_from_results: ScoreItem = Field(
        description="Conclusions follow from results and discussion."
    )
    conclusions_clear: ScoreItem = Field(description="Conclusions clear and unambiguous.")
    references_properly_attributed: ScoreItem = Field(
        description="References properly attributed and listed."
    )
    sentence_paragraph_length: ScoreItem = Field(
        description="Sentence and paragraph length appropriate."
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def average(self) -> float:
        scores = [
            self.results_clearly_stated.score,
            self.results_free_of_discussion.score,
            self.graphs_and_tables_proper.score,
            self.sufficient_results.score,
            self.discussion_relates_to_others.score,
            self.discussion_length_appropriate.score,
            self.conclusions_follow_from_results.score,
            self.conclusions_clear.score,
            self.references_properly_attributed.score,
            self.sentence_paragraph_length.score,
        ]
        return round(sum(scores) / len(scores), 2)


class BaselineMeasures(ApiModel):
    """The four baseline measures recorded on every Budinski document review."""

    purpose_distinct_from_objective: bool = Field(
        description=(
            "States the purpose of the report explicitly, distinct from the objective of the work."
        )
    )
    procedure_repeatable: bool = Field(
        description="Procedure detailed enough for another competent party to repeat the work."
    )
    conclusions_valid: bool = Field(
        description="Conclusions are conclusions, not results and not discussion."
    )
    recommendations_actionable: bool = Field(
        description="Recommendations name an owner and a date."
    )
    reasons: dict[str, str] = Field(
        default_factory=dict,
        description="Detailed rationale and evidence for each baseline measure.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> int:
        """Count of passing baseline measures (0 to 4)."""
        return sum([
            self.purpose_distinct_from_objective,
            self.procedure_repeatable,
            self.conclusions_valid,
            self.recommendations_actionable,
        ])

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary_ratio(self) -> str:
        """String representation of baseline score, e.g., '1/4' or '1 of 4'."""
        return f"{self.score}/4"


class BudinskiScorecard(ApiModel):
    """Automated scorecard evaluating the 41 Appendix 12 items across 4 groups."""

    technical_content: TechnicalContentGroup | None = None
    style: StyleGroup | None = None
    report_mechanics: ReportMechanicsGroup | None = None
    conclusions_and_craft: ConclusionsAndCraftGroup | None = None

    # Phase-1 flat representation. The grouped fields above remain available
    # for the current evaluator and export path while the refactor migrates.
    items: list[ScorecardEntry] = Field(default_factory=list)

    group_i_average: float = Field(default=0.0, description="Average score for Group I.")
    group_ii_average: float = Field(default=0.0, description="Average score for Group II.")
    group_iii_average: float = Field(default=0.0, description="Average score for Group III.")
    group_iv_average: float = Field(default=0.0, description="Average score for Group IV.")
    overall_average: float = Field(default=0.0, description="Overall average score (1-5).")

    baseline_measures: BaselineMeasures | None = Field(
        default=None, description="Standing 4 baseline measures."
    )
    blockers_count: int = Field(default=0, description="Count of blocking findings.")
    majors_count: int = Field(default=0, description="Count of major findings requiring fix.")
    minors_count: int = Field(default=0, description="Count of minor/language findings.")
    review_score_string: str = Field(
        default="",
        description="Formatted summary line (REVIEWSCORE | doc=... | rev=... | ...).",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def baseline_score(self) -> float:
        """Return the number of passing baseline measures out of four."""
        if self.baseline_measures is not None:
            return float(self.baseline_measures.score)
        baseline_items = [
            item for item in self.items if item.group.lower() in {"baseline", "baselines"}
        ]
        return float(sum(item.score >= 3 for item in baseline_items))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def group_averages(self) -> dict[str, float]:
        """Return deterministic averages for Groups I, II, III, and IV."""
        group_names = {
            "Group I": "group_i_average",
            "Group II": "group_ii_average",
            "Group III": "group_iii_average",
            "Group IV": "group_iv_average",
        }
        averages: dict[str, float] = {}
        for group, legacy_field in group_names.items():
            entries = [item.score for item in self.items if item.group == group]
            averages[group] = round(sum(entries) / len(entries), 2) if entries else float(
                getattr(self, legacy_field)
            )
        return averages

    def get_all_items(self) -> list[tuple[str, str, ScoreItem]]:
        """Return all 41 items as a flat list of (group_name, item_key, ScoreItem)."""
        items: list[tuple[str, str, ScoreItem]] = []
        for group_name, group in (
            ("Technical Content", self.technical_content),
            ("Style", self.style),
            ("Report Mechanics", self.report_mechanics),
            ("Conclusions & Craft", self.conclusions_and_craft),
        ):
            if group is None:
                continue
            for key in type(group).model_fields:
                val = getattr(group, key)
                if isinstance(val, ScoreItem):
                    items.append((group_name, key, val))
        items.extend(
            (
                item.group,
                item.item_id,
                ScoreItem(name=item.item_id, score=item.score, note=item.note),
            )
            for item in self.items
        )
        return items

    def get_rework_items(self) -> list[tuple[str, str, ScoreItem]]:
        """Return all checklist items scoring 2 or below (treated as requiring rework)."""
        return [(grp, key, item) for grp, key, item in self.get_all_items() if item.score <= 2]


class BlockerFinding(ApiModel):
    """A blocking finding that prevents the document from being relied upon as issued."""

    number: int = Field(default=1, description="Blocker number (e.g. 1, 2).")
    title: str = Field(description="Blocker title summary.")
    where_location: str = Field(description="Location in document.")
    what_it_says: str = Field(description="Text as written in document.")
    what_body_has: str = Field(description="What the body/definition tables actually define.")
    why_it_matters: str = Field(description="Engineering consequence of the discrepancy.")
    what_would_fix_it: str = Field(description="Required action to resolve.")


class MajorFinding(ApiModel):
    """A major finding to fix in the next revision."""

    number: int = Field(description="Finding number (1 to N).")
    finding: str = Field(description="Description of finding.")
    what_would_fix_it: str = Field(description="Actionable correction.")


class LanguageFinding(ApiModel):
    """A minor language or mechanics finding."""

    page: str = Field(description="Page number(s) where error occurs.")
    as_written: str = Field(description="Text as written.")
    suggested: str = Field(description="Suggested correction.")


class DemonstrationRewrite(ApiModel):
    """Demonstration rewrite comparing original section against Budinski standard."""

    section_title: str = Field(
        default="§7.1 Conclusions", description="Section heading being rewritten."
    )
    intro_note: str = Field(
        default="", description="Introductory context for the demonstration."
    )
    as_written_title: str = Field(default="AS WRITTEN (PRINTED PAGE 28, ABRIDGED)")
    as_written_text: str = Field(description="Original section text.")
    faults_summary: str = Field(description="Summary of faults against Budinski rules.")
    demonstration_title: str = Field(
        default="DEMONSTRATION — THE SAME CONTENT AS CONCLUSIONS"
    )
    demonstration_items: list[str] = Field(
        default_factory=list, description="List of rewritten single sentences."
    )
    conclusion_summary: str = Field(description="Summary explanation of demonstration rewrite.")


class AssessmentMetadata(ApiModel):
    """Metadata block for the document under review."""

    document_reviewed: str = Field(description="Full identity string of the reviewed document.")
    type_of_review: str = Field(
        default=(
            "Technical writing review only. Structure, evidence traceability, "
            "and reporting convention."
        )
    )
    basis: str = Field(
        default=(
            "Appendix 12 checklist, plus Chapters 9, 10, 11 and 13 of the guide. "
            "Procedure per CLAUDE.md Steps 0–7."
        )
    )
    scoring: str = Field(
        default=(
            "1 = disagree, 5 = agree. Any item at 2 or below is treated as requiring rework. "
            "The same 41 checklist items used on reports 01, 02 and 03, so the four are "
            "directly comparable."
        )
    )
    note: str = Field(
        default=(
            "The cover names the reviewer of this document in the Checked column. "
            "This review is an input to that named review, not a substitute for it."
        )
    )
    not_covered: str = Field(
        default="The engineering itself. See Limits of this review on the last page."
    )


class AssessmentData(ApiModel):
    """Full data model required to generate a complete Review-ALE DOCX report."""

    title: str = Field(
        default="Review of Asset Life Extension Study, Grissik Plant Static Equipment"
    )
    subtitle: str = Field(
        default=(
            "Scored against the document review checklist of Budinski, "
            "Engineers' Guide to Technical Writing (2001), Appendix 12"
        )
    )
    header_title: str = Field(default="DOCUMENT REVIEW · ENGINEERING")
    running_header: str = Field(
        default=(
            "Review of ALE Study Grissik Static Equipment, "
            "Doc. ID-N-CG-MM1-DSR-PL-00-3001 Rev A — writing review only"
        )
    )
    metadata: AssessmentMetadata
    summary_judgement: list[str] = Field(
        default_factory=list, description="Paragraphs of summary judgement."
    )
    bottom_line: str = Field(description="Bottom line callout text.")
    baseline_measures: BaselineMeasures
    blockers: list[BlockerFinding] = Field(default_factory=list)
    major_findings: list[MajorFinding] = Field(default_factory=list)
    language_findings: list[LanguageFinding] = Field(default_factory=list)
    demonstration_rewrite: DemonstrationRewrite | None = None
    scorecard: BudinskiScorecard
    what_it_does_well: list[str] = Field(default_factory=list)
    limits_of_review: list[str] = Field(default_factory=list)
    review_score_string: str = Field(default="")
