from collections.abc import Sequence
from typing import Any

from schemas.budinski import (
    AssessmentData,
    AssessmentMetadata,
    BaselineMeasures,
    BlockerFinding,
    BudinskiScorecard,
    ConclusionsAndCraftGroup,
    DemonstrationRewrite,
    LanguageFinding,
    MajorFinding,
    ReportMechanicsGroup,
    ScoreItem,
    StyleGroup,
    TechnicalContentGroup,
)
from schemas.extraction import LayoutAnomaly
from services.budinski_evaluator import BudinskiEvaluator


class CanonicalEvaluator(BudinskiEvaluator):
    def evaluate_41_checklist_items(
        self,
        doc_sections: dict[str, Any],
        layout_anomalies: Sequence[LayoutAnomaly | dict[str, Any]] | None = None,
    ) -> BudinskiScorecard:
        return self._build_ale_baseline_scorecard(doc_sections, layout_anomalies or [])

    def _build_ale_baseline_scorecard(
        self,
        doc_sections: dict[str, Any],
        anomalies: Sequence[LayoutAnomaly | dict[str, Any]],
    ) -> BudinskiScorecard:
        """Construct the exact 41-item scorecard matching the Review-ALE baseline report."""
        tech = TechnicalContentGroup(
            message_clear=ScoreItem(
                name="The message to the reader is clear",
                score=4,
                note=(
                    "The Executive Summary answers the question, but runs four pages "
                    "and repeats §6 in full."
                ),
            ),
            logical_approach=ScoreItem(
                name="The engineering approach is logical",
                score=5,
                note=(
                    "RUL → criticality → RBI risk → priority matrix → recommended activity. "
                    "Each step is defined before it is used."
                ),
            ),
            adequate_research=ScoreItem(
                name="Adequate research of previous work",
                score=3,
                note=(
                    "The 2017 DNV GL ALE is used as the baseline and its structure "
                    "deliberately retained. No reference list."
                ),
            ),
            adequate_comparison=ScoreItem(
                name="Adequate comparison with the work of others",
                score=3,
                note="Compared against the 2017 study only; no external benchmark.",
            ),
            conclusions_supported=ScoreItem(
                name="Conclusions are supported by the work",
                score=3,
                note=(
                    "Every count reconciles exactly, but conclusion 3 contradicts "
                    "the definition tables."
                ),
            ),
            value_stated=ScoreItem(
                name="The value of the work is clearly stated",
                score=5,
                note=(
                    "A 2040 extension target, stated in the first paragraph and carried throughout."
                ),
            ),
            objective_met=ScoreItem(
                name="The work met the stated objective",
                score=5,
                note="All four §2.2 objectives are addressed and evidenced.",
            ),
            original_free_of_plagiarism=ScoreItem(
                name="Original and free of plagiarism",
                score=4,
                note="ASME formulas reproduced with the code named at each one; no reference list.",
            ),
            timely=ScoreItem(
                name="Timely",
                score=4,
                note="Cover date 21 August 2026; file produced 3 September 2026.",
            ),
        )

        style = StyleGroup(
            objective_tone=ScoreItem(
                name="Objective, neutral tone",
                score=5,
                note="Consistent throughout. No overselling of the life-extension result.",
            ),
            sections_logical=ScoreItem(
                name="Sections are logical",
                score=4,
                note="Seven chapters in a sound order. No reference section.",
            ),
            readership_level=ScoreItem(
                name="Writing level suits the readership",
                score=5,
                note="Correctly pitched for an asset integrity engineer.",
            ),
            free_of_jargon=ScoreItem(
                name="Free of jargon and commercialism",
                score=4,
                note=(
                    "§2.5 abbreviation list is thorough. The TSA anomaly monitoring programme "
                    "in recommendation 9 is never described."
                ),
            ),
            english_usage=ScoreItem(
                name="Use of English is satisfactory",
                score=2,
                note=(
                    "Faults reach the Executive Summary and two actioned recommendations. "
                    "See the language table."
                ),
            ),
            concise=ScoreItem(
                name="Understandable and concise",
                score=3,
                note="The Executive Summary reproduces §6 at length; §7.1 reproduces it again.",
            ),
            interesting=ScoreItem(
                name="Interesting",
                score=4,
                note="Table 3-1 and Table 3-2 are the strongest idea in the sample.",
            ),
            free_of_personal_opinion=ScoreItem(
                name="Free of personal opinion and figures of speech",
                score=5,
                note="No lapses found.",
            ),
            no_over_explain=ScoreItem(
                name="Does not over-explain",
                score=3,
                note="The same counts appear three times — Executive Summary, §6, §7.1.",
            ),
            standard_writing_practice=ScoreItem(
                name="Conforms to standard writing practice",
                score=2,
                note=(
                    "No reference list; 21 unidentified pages; front lists do not "
                    "navigate to the body."
                ),
            ),
            layout_and_whitespace=ScoreItem(
                name="Page layout and white space acceptable",
                score=3,
                note=(
                    "Appendix divider titles sit at the foot of otherwise blank pages; "
                    "the landscape tables carry no headers."
                ),
            ),
        )

        mech = ReportMechanicsGroup(
            sufficient_background=ScoreItem(
                name="Sufficient background information",
                score=5,
                note=(
                    "§2.1 gives 1998 commissioning, the 20-year design life, the 2017 DNV GL "
                    "extension to 2028, the change of operator and the post tie-in context."
                ),
            ),
            purpose_of_work_clear=ScoreItem(
                name="Purpose of the work is clear",
                score=5,
                note="To determine whether the plant can be extended to 2040.",
            ),
            objective_of_work_clear=ScoreItem(
                name="Objective of the work is clear",
                score=5,
                note="§2.2, four numbered objectives.",
            ),
            purpose_of_report_clear=ScoreItem(
                name="Purpose of the report is clear",
                score=1,
                note="Never stated.",
            ),
            objective_of_report_clear=ScoreItem(
                name="Objective of the report is clear",
                score=3,
                note="Inferable from §2.3 Scope of Works.",
            ),
            format_stated=ScoreItem(
                name="Format of the report is stated",
                score=1,
                note="Absent.",
            ),
            work_referenced=ScoreItem(
                name="Work of others adequately referenced",
                score=1,
                note="No reference section anywhere in the document.",
            ),
            experimental_steps_outlined=ScoreItem(
                name="Experimental steps clearly outlined",
                score=5,
                note="§3, §3.1 and §5.5 to §5.7 define every step before it is applied.",
            ),
            adequate_detail_to_repeat=ScoreItem(
                name="Adequate detail for others to repeat the work",
                score=5,
                note=(
                    "Five tmin formulas with symbols, corrosion-rate hierarchy, RUL equation, "
                    "fifteen assumptions, tie-breaking rules, and the >20-year cap with its "
                    "regulatory basis. Best in the sample."
                ),
            ),
            free_of_trade_names=ScoreItem(
                name="Free of unnecessary trade names and detail",
                score=4,
                note="PCMS is named appropriately as the client's own system.",
            ),
            test_standards_cited=ScoreItem(
                name="Test standards properly cited",
                score=3,
                note=(
                    "ASME VIII Div 1, ASME BPVC II-D, API 580, API 581, API 579-1 and ASME PCC-1 "
                    "are named by number. No edition year for any, and none listed."
                ),
            ),
        )

        craft = ConclusionsAndCraftGroup(
            results_clearly_stated=ScoreItem(
                name="Results clearly stated and illustrated where needed",
                score=5,
                note=(
                    "Twenty-one tables and eight figures; a decision matrix for each of "
                    "the three populations."
                ),
            ),
            results_free_of_discussion=ScoreItem(
                name="Results free of procedure detail and discussion",
                score=4,
                note="§6 is clean results with short interpretive summaries.",
            ),
            graphs_and_tables_proper=ScoreItem(
                name="Graphs and tables necessary and properly made",
                score=3,
                note=(
                    "Numbering is complete and unduplicated — better than report 03 — but "
                    "page references drift and no caption cites a data source."
                ),
            ),
            sufficient_results=ScoreItem(
                name="Sufficient results presented",
                score=5,
                note=(
                    "Component-level detail for all 175 components, with the supporting "
                    "data in the appendices."
                ),
            ),
            discussion_relates_to_others=ScoreItem(
                name="Discussion relates this work to the findings of others",
                score=2,
                note="Only the 2017 ALE. No discussion chapter exists.",
            ),
            discussion_length_appropriate=ScoreItem(
                name="Discussion neither too long nor too short",
                score=2,
                note=(
                    "There is no discussion section; interpretation is distributed through "
                    "the §6 summaries."
                ),
            ),
            conclusions_follow_from_results=ScoreItem(
                name="Conclusions follow from results and discussion",
                score=3,
                note="Arithmetically they do; conclusion 3 contradicts the definition tables.",
            ),
            conclusions_clear=ScoreItem(
                name="Conclusions clear and unambiguous",
                score=2,
                note=(
                    "Items 4 to 6 are restated results carrying six figure and table references; "
                    "item 3 misstates a band."
                ),
            ),
            references_properly_attributed=ScoreItem(
                name="References properly attributed and listed",
                score=1,
                note="No reference section.",
            ),
            sentence_paragraph_length=ScoreItem(
                name="Sentence and paragraph length appropriate",
                score=4,
                note="Well controlled; the faults are grammatical rather than structural.",
            ),
        )

        baselines = BaselineMeasures(
            purpose_distinct_from_objective=False,
            procedure_repeatable=True,
            conclusions_valid=False,
            recommendations_actionable=False,
            reasons={
                "purpose_distinct_from_objective": (
                    "§2.2 (p9) is headed 'Objective' and gives the objective of the study — to "
                    "evaluate long-term integrity and develop an ALE roadmap. Nothing states "
                    "what the document itself is for or who is to act on it."
                ),
                "procedure_repeatable": (
                    "The strongest in the sample. §5.5 gives all five tmin formulas with every "
                    "symbol defined against ASME VIII Div 1; §5.6 gives the three-tier "
                    "corrosion-rate hierarchy and when each tier applies; §5.7 gives the RUL "
                    "equation; §3 gives the priority rules in both prose and matrix form; §3.1 "
                    "gives the tie-breaking rules; §4 gives fifteen numbered assumptions "
                    "including the constant-rate assumption and the >20-year reporting cap "
                    "with its regulatory basis."
                ),
                "conclusions_valid": (
                    "§7.1 items 4, 5 and 6 (p28) restate the §6 result tables in full, with six "
                    "table and figure references between them. Item 3 misstates a definition "
                    "band. Ch 11 asks for numbered single sentences with no figure reference "
                    "and no new material."
                ),
                "recommendations_actionable": (
                    "Ten recommendations at §7.2 (pp29–30). None names an owner. Dates are "
                    "present on several — 'every 3 – 5 years', 'before the end of 2027', "
                    "'by end-2027' — which is the best date discipline in the sample; only the "
                    "owner column is missing."
                ),
            },
        )

        g1_avg = 4.00
        g2_avg = 3.64
        g3_avg = 3.45
        g4_avg = 3.10
        overall_avg = 3.54
        blockers = 2
        majors = 12
        minors = 15

        score_string = (
            "REVIEWSCORE | doc=ID-N-CG-MM1-DSR-PL-00-3001 | rev=A | date=2026-08-21 | "
            f"I={g1_avg:.2f} II={g2_avg:.2f} III={g3_avg:.2f} IV={g4_avg:.2f} | "
            f"baseline=1/4 | blockers={blockers} majors={majors} minors={minors}"
        )

        return BudinskiScorecard(
            technical_content=tech,
            style=style,
            report_mechanics=mech,
            conclusions_and_craft=craft,
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


def create_canonical_ale_assessment_data() -> AssessmentData:
    """Return the complete, canonical AssessmentData matching the Review-ALE baseline report."""
    evaluator = CanonicalEvaluator()
    scorecard = evaluator._build_ale_baseline_scorecard({}, [])

    meta = AssessmentMetadata(
        document_reviewed=(
            "Asset Life Extension Study for Grissik Plant — Assessment Report for Static Equipment "
            "· MEDCO Doc. No. ID-N-CG-MM1-DSR-PL-00-3001 · Rev A, IFR, 21/08/2026 · 34 numbered "
            "pages in a 56-page file · Originator PT LAPI ITB for Medco E&P Grissik Ltd"
        ),
        type_of_review=(
            "Technical writing review only. Structure, evidence traceability, and reporting "
            "convention."
        ),
        basis=(
            "Appendix 12 checklist, plus Chapters 9, 10, 11 and 13 of the guide. Procedure per "
            "CLAUDE.md Steps 0–7."
        ),
        scoring=(
            "1 = disagree, 5 = agree. Any item at 2 or below is treated as requiring rework. "
            "The same 41 checklist items used on reports 01, 02 and 03, so the four are "
            "directly comparable."
        ),
        note=(
            "The cover names the reviewer of this document in the Checked column. This review "
            "is an input to that named review, not a substitute for it."
        ),
        not_covered="The engineering itself. See Limits of this review on the last page.",
    )

    summary_judgement = [
        (
            "On arithmetic this is the cleanest document in the sample, and it is not close. "
            "I traced the full counting chain and every figure reconciles exactly: the component "
            "and equipment totals in Table 2-1 (121 + 54 = 175, 94 + 38 = 132), the population "
            "split in Table 2-2 (27 + 112 + 36 = 175), the criticality counts across Tables 1-1 "
            "to 1-3 (25 + 97 + 36 = 158 at Criticality 4, 2 + 14 + 0 = 16 at Criticality 3), the "
            "decision matrix at Table 6-2, and — the hard one — all five ALE priority counts, "
            "which I re-derived from Table 6-2 by applying the Table 3-1 rules and got 0, 21, 83, "
            "37 and 34, matching the report exactly and summing to 175. No other report reviewed "
            "has survived that. The methodology is also genuinely reproducible: five "
            "minimum-thickness formulas with every symbol defined, a three-tier corrosion-rate "
            "hierarchy, the RUL equation, fifteen numbered assumptions, and explicit "
            "tie-breaking rules at §3.1. Table 3-1 and Table 3-2, taken together, are the best "
            "single artefact in the sample — they convert engineering judgement into a rule a "
            "third party can apply and audit."
        ),
        (
            "The faults are in closure and navigation. The file is named Rev B; the document says "
            "Rev A; the Revision Sheet is twenty blank rows, so the document does not record its "
            "own revision history. The front matter no longer points at the body — 15 of the 28 "
            "figure and table page references are wrong, and the contents page is wrong for §6.4 "
            "onward and for all five appendices. Twenty-one pages of appendix data carry no page "
            "number, no header and no document number at all. There is no reference section, "
            "though the work rests on ASME VIII Div 1, ASME BPVC II-D, API 580, API 581, "
            "API 579-1, ASME PCC-1 and a named Indonesian ministerial decision. And the "
            "Conclusions state the Criticality 2 band as 6 to 14 years when every definition "
            "table in the document gives it as 0 to 6 years — an eight-year error in the "
            "description of the single most time-critical component in the study."
        ),
    ]

    bottom_line = (
        "Fix conclusion 3 on printed page 28 before reissue. It states that 35-V-101 SHELL is "
        "Criticality 2 with a remaining life of 6 to 14 years, while Table 1-2 and Table 3-1 both "
        "define Criticality 2 as 0 to 6 years. That component is the one item in the study that "
        "does not reach the 2040 target, and the Conclusions describe it as though it does."
    )

    blockers = [
        BlockerFinding(
            number=1,
            title=(
                "THE CONCLUSIONS GIVE THE CRITICALITY 2 BAND AS 6 TO 14 YEARS; "
                "EVERY DEFINITION TABLE GIVES 0 TO 6"
            ),
            where_location="§7.1 conclusion 3, printed page 28.",
            what_it_says=(
                "“1 static component 35-V-101 shell is classified as Criticality 2 "
                "(6 < RUL ≤ 14 yrs), and 16 static components are classified as "
                "Criticality 3 (6 < RUL ≤ 14 yrs)”. The same band is given for both classes."
            ),
            what_body_has=(
                "Table 1-1, Table 1-2 and Table 1-3 (pp6) all define Criticality 2 as "
                "“0 < RUL 2026 ≤ 6 yr (to 2032)” and Criticality 3 as “6 < RUL 2026 ≤ 14 yr "
                "(to 2040)”. Table 3-1 (p12) repeats “Criticality 2 (0 < RUL ≤ 6 yrs)”. "
                "The Executive Summary at printed page 6 uses the correct band."
            ),
            why_it_matters=(
                "35-V-101 SHELL is the single Criticality 2 component in a population of 175, and "
                "the Executive Summary already singles it out: “It is strongly recommended that "
                "MEPG verify the component thickness before determining any further action.” "
                "Read as written, conclusion 3 places it in the 6-to-14-year band, which reaches "
                "the 2040 target. Under the report's own definition it is in the 0-to-6-year band, "
                "which does not — it reaches minimum thickness by about 2032. A reader who reads "
                "only the Conclusions, which is what most recipients of a life-extension study "
                "will do, takes away the opposite of what the assessment found."
            ),
            what_would_fix_it=(
                "Correct the band in conclusion 3 to “0 < RUL ≤ 6 yrs”, and add a sentence "
                "stating plainly that one component of the 175 is not projected to reach the "
                "2040 target on the current corrosion rate, and that Recommendation 5 covers it."
            ),
        ),
        BlockerFinding(
            number=2,
            title="THE DOCUMENT DOES NOT RECORD ITS OWN REVISION",
            where_location=(
                "Cover page (unnumbered) and Revision Sheet, printed page 1. "
                "Also the supplied filename."
            ),
            what_it_says=(
                "The cover revision block carries a single row: “A · IFR · 21/08/2026 · Issued "
                "For Review”. The Revision Sheet on printed page 1 is headed Revision / Date / "
                "Description of Change and contains twenty entirely blank rows."
            ),
            what_body_has=(
                "The file supplied for review is named “05.MEPG-Asset Life Extension 2026_Static "
                "Equipment_RevB.pdf” and its PDF creation date is 3 September 2026, thirteen "
                "days after the cover issue date. Nothing inside the document identifies a Rev B, "
                "and no change record exists for one."
            ),
            why_it_matters=(
                "Either this is Rev A and the filename is wrong, or it is Rev B and neither the "
                "cover, the revision block nor the Revision Sheet says so. Under a "
                "controlled-document system the wrong version gets filed and actioned, and there "
                "is no record of what changed between issues — which is the specific thing a "
                "Revision Sheet exists to prevent. This is the same fault recorded on report 03, "
                "where the cover said Final Report against an Issued for Review status block."
            ),
            what_would_fix_it=(
                "Set the revision on the cover, the revision block and the Revision Sheet to one "
                "value, and complete at least one Revision Sheet row describing the change from "
                "the previous issue. If this is the first issue, record “Rev A — first issue for "
                "review” rather than leaving the sheet blank."
            ),
        ),
    ]

    major_findings = [
        MajorFinding(
            number=1,
            finding=(
                "The front matter no longer navigates to the body. Of 28 comparable List of "
                "Figures and List of Tables entries, 15 carry the wrong page number — every "
                "entry from Table 6-2 and Figure 6-2 onward, drifting from one page to two. "
                "The Table of Contents is wrong for §6.4 (says 22, is 24), §6.5 and §6.6 (says "
                "24, is 26), §7 (says 26, is 28), §7.1 and §7.2, and for all five appendices, "
                "each of which is understated by two."
            ),
            what_would_fix_it=(
                "Regenerate the Table of Contents, List of Figures and List of Tables from the "
                "final paginated document rather than updating them by hand. This was found by "
                "script; reading catches perhaps three of fifteen, which is why it survives "
                "review."
            ),
        ),
        MajorFinding(
            number=2,
            finding=(
                "Twenty-one of the fifty-six pages in the file carry no page number, no running "
                "header and no document number. These are the landscape data pages inside "
                "Appendices A to E. Only the five appendix divider pages are numbered, as printed "
                "pages 30 to 34; the data pages between them carry nothing."
            ),
            what_would_fix_it=(
                "Apply the running header and footer to the landscape pages. Under a "
                "controlled-document system an unidentified page is an uncontrolled page, and a "
                "detached sheet cannot be traced back to this report — a QMS reviewer may "
                "reasonably treat this as a hold point rather than a revision item."
            ),
        ),
        MajorFinding(
            number=3,
            finding=(
                "There is no reference section anywhere in the document. The assessment relies "
                "on ASME Section VIII Div 1, ASME BPVC Section II Part D, API 580, API 581, "
                "API 579-1/ASME FFS-1, ASME PCC-1, the 2017 DNV GL asset life extension study, "
                "and Decision of the Ministry of Energy and Mineral Resources No. "
                "183.K/HK.02/DMT/2024. None is listed, and no edition or year is given for any "
                "code."
            ),
            what_would_fix_it=(
                "Add a numbered reference section after §7, giving each code with its edition "
                "year, and cite each at the point of use — the tmin formulas at §5.5, the RBI "
                "methodology at §2.1 and the service-life cap at §4 item 3."
            ),
        ),
        MajorFinding(
            number=4,
            finding=(
                "The purpose of the report is never stated. §2.2 (p9) is headed “Objective” and "
                "gives the objective of the study. Ch 9 treats purpose and objective as "
                "different things: purpose is what the document is for, objective is what the "
                "work was for."
            ),
            what_would_fix_it=(
                "Add two sentences at the head of §2.2 stating what the document is for and who "
                "is to act on it, then keep the existing four items under “Objectives”."
            ),
        ),
        MajorFinding(
            number=5,
            finding=(
                "No statement of what the report contains and in what order. Ch 9 lists the "
                "format of what follows as one of the five ingredients of an introduction, and "
                "this document has seven chapters and five appendices."
            ),
            what_would_fix_it="Add a short paragraph at the end of §2.3.",
        ),
        MajorFinding(
            number=6,
            finding=(
                "§7.1 conclusions 4, 5 and 6 (p28) restate the §6 result tables in full — "
                "criticality counts a to d and priority counts a to e for each of the three "
                "populations — carrying six table and figure references between them. Ch 11: "
                "conclusions are numbered single sentences inferred from results, never a "
                "figure reference and never new material. This is the third consecutive report "
                "in which Conclusions is the section carrying the highest-severity structural "
                "fault, which points at the template rather than the author."
            ),
            what_would_fix_it=(
                "Reduce §7.1 to numbered single sentences stating what was learned. The counts "
                "stay in §6, where they already are. See the demonstration."
            ),
        ),
        MajorFinding(
            number=7,
            finding=(
                "None of the ten recommendations at §7.2 names an owner. Recommendation 10 is a "
                "scope limitation, not a recommendation. Recommendation 7 says to update the "
                "ranking “using the results of Priority 1 and Priority 2 inspections”, but the "
                "report states in three places that no component is classified as Priority 1. "
                "Recommendation 5 is grammatically incomplete: “Inspect and verify the 21 static "
                "components within classified as Priority by end-2027.”"
            ),
            what_would_fix_it=(
                "Add an Owner column, blank for the author to complete. Move recommendation 10 "
                "to §2.4. Delete the Priority 1 clause from recommendation 7. Complete "
                "recommendation 5 to read “…classified as Priority 2 by end 2027.”"
            ),
        ),
        MajorFinding(
            number=8,
            finding=(
                "The Criticality 1 band is defined two ways. Table 3-1 (p12) gives “Criticality 1 "
                "(RUL < 0 yrs)”. Tables 1-1, 1-2 and 1-3 (p6) give “RUL 2026 ≤ 0 yr”. "
                "Conclusion 1 (p28) gives “RUL ≤ 0 yrs”. A component with RUL of exactly zero "
                "is Criticality 1 under two of these and unclassified under the third, because "
                "Criticality 2 begins above zero."
            ),
            what_would_fix_it=(
                "Use “RUL ≤ 0” in all three places. No component is currently affected, which is "
                "why this survived — it will not stay that way over the life of the programme."
            ),
        ),
        MajorFinding(
            number=9,
            finding=(
                "The Executive Summary (p5) states that the assessment “was performed with "
                "limitations and assumptions, as described in section 2.4”. §2.4 contains only "
                "Table 2-3, a list of excluded components. The fifteen assumptions are in §4. "
                "The site-survey limitation named in the Executive Summary appears in §4 item 5, "
                "not in §2.4 either."
            ),
            what_would_fix_it=(
                "Point the cross-reference at §4, or move the assumptions into §2.4 and "
                "retitle it “Limitations and Assumptions”."
            ),
        ),
        MajorFinding(
            number=10,
            finding=(
                "The one exception to the headline finding is never stated as an exception. The "
                "Executive Summary concludes that the population is “suitable for operation "
                "until 2040 with continued monitoring”, and conclusion 2 reports 90.29% with "
                "more than fourteen years of life “demonstrating strong overall alignment with "
                "the 2040 target”. The single Criticality 2 component sits in the 0-to-6-year "
                "band, reaching minimum thickness around 2032, and this is never said in plain "
                "words anywhere in the document."
            ),
            what_would_fix_it=(
                "One sentence in the Executive Summary and one in §7.1: state that 174 of 175 "
                "components are projected to reach 2040 on current corrosion rates, that one is "
                "not, and that Recommendation 5 addresses it."
            ),
        ),
        MajorFinding(
            number=11,
            finding=(
                "Appendix C reports corrosion rates to nine decimal places — 0.657657658 mm/y for "
                "35-V-101 SHELL — while the Executive Summary quotes the same component's rate as "
                "0.65 mm/year, which is the truncation rather than the rounding of that figure. "
                "No rounding or significant-figure convention is stated anywhere."
            ),
            what_would_fix_it=(
                "State a convention — two decimal places for corrosion rates in the body is "
                "normal — and apply it in both the appendix and the text. The measurement does "
                "not support nine decimals and the mismatch between 0.65 and 0.66 invites a "
                "reader to doubt the table."
            ),
        ),
        MajorFinding(
            number=12,
            finding=(
                "§4 items 6 and 7 say the same thing. Item 6: the study “does not consider all "
                "possible operational issues and scenarios outside of the safe operating "
                "limits”. Item 7: “The study does not consider operational scenarios outside the "
                "safe operating limits.”"
            ),
            what_would_fix_it="Delete one.",
        ),
    ]

    language_findings = [
        LanguageFinding(
            page="5",
            as_written=(
                "“This assessment was performed with limitations and assumptions, as described "
                "in section 2.4.”"
            ),
            suggested=(
                "“…as described in Section 4.” The assumptions are not in §2.4. See finding 9."
            ),
        ),
        LanguageFinding(
            page="6",
            as_written=(
                "“One component is classified as Criticality 2 with indirectly impacted by post "
                "tie-in condition”"
            ),
            suggested=(
                "“One component, indirectly impacted by the post tie-in condition, is classified "
                "as Criticality 2”."
            ),
        ),
        LanguageFinding(
            page="7",
            as_written=(
                "“A total of 158 static equipment component is classified as Criticality 4.”"
            ),
            suggested=(
                "“A total of 158 static equipment components are classified as Criticality 4.”"
            ),
        ),
        LanguageFinding(
            page="7, 8",
            as_written=(
                "“A total of 21 components is classified as Priority 2, comprising by 2 "
                "components directly impacted…”"
            ),
            suggested=(
                "“A total of 21 components are classified as Priority 2, comprising 2 directly "
                "impacted…”. The construction “comprising by” recurs in all four priority "
                "paragraphs."
            ),
        ),
        LanguageFinding(
            page="8",
            as_written=(
                "“…comprising by 9 component directly impacted, 21 components indirectly impacted…”"
            ),
            suggested="“…comprising 9 components directly impacted…”",
        ),
        LanguageFinding(
            page="12",
            as_written=(
                "“The 2026 ALE priority is a designed to prioritize asset integrity activities "
                "by combining RUL and RBI to determine recommendations activity”"
            ),
            suggested=(
                "“The 2026 ALE priority is designed to prioritise asset integrity activities "
                "by combining RUL and RBI to determine the recommended activity”."
            ),
        ),
        LanguageFinding(
            page="14",
            as_written=(
                "“…therefore for equipment which is have RUL more than 20 years, will be noted "
                "as ‘>20 years’.”"
            ),
            suggested=(
                "“…therefore equipment with a RUL greater than 20 years is recorded as "
                "‘>20 years’.”"
            ),
        ),
        LanguageFinding(
            page="20",
            as_written=(
                "“…classified as high risk and increased by 3 into five static equipment "
                "components by 2040.”"
            ),
            suggested=(
                "“…classified as high risk, increasing by three to five components by 2040.”"
            ),
        ),
        LanguageFinding(
            page="22",
            as_written=(
                "“15 (fifteen) components are classified as high risk and increased into 19 "
                "(nine-teen) static equipment components”"
            ),
            suggested=(
                "“…increasing to 19 (nineteen) static equipment components”. “nine-teen” is "
                "broken across a hyphen."
            ),
        ),
        LanguageFinding(
            page="28",
            as_written=(
                "“The design and operation of 132 equipment items were evaluated. This "
                "evaluation covered the following:”"
            ),
            suggested=(
                "The list that follows is findings, not scope. “…were evaluated. The evaluation "
                "found the following:”"
            ),
        ),
        LanguageFinding(
            page="28",
            as_written="“The summary of 202 7 directly impacted by post tie-in condition…”",
            suggested="“2027”. The numeral is broken by a space.",
        ),
        LanguageFinding(
            page="29",
            as_written=(
                "“8. 21 of 175 static components are classified as Priority 2 require "
                "near-term inspection.”"
            ),
            suggested=(
                "“21 of 175 static components are classified as Priority 2 and require "
                "near-term inspection.”"
            ),
        ),
        LanguageFinding(
            page="29",
            as_written=(
                "“Of the 21 static components are classified as Priority 2, 16 static components "
                "Criticality 4–High Risk are scheduled for earlier inspection”"
            ),
            suggested=(
                "“Of the 21 static components classified as Priority 2, 16 are Criticality 4 "
                "at High risk and are scheduled for earlier inspection”."
            ),
        ),
        LanguageFinding(
            page="29",
            as_written=(
                "“Inspect and verify the 21 static components within classified as Priority "
                "by end-2027.”"
            ),
            suggested=(
                "“Inspect and verify the 21 static components classified as Priority 2 by "
                "end 2027.” A recommendation that will be actioned should not have a word missing."
            ),
        ),
        LanguageFinding(
            page="3, 4",
            as_written=(
                "Several List of Figures and List of Tables rows carry doubled dotted leaders, "
                "and “prioritize” at §3 sits against “programme” in Table 3-2 and “program” "
                "everywhere else."
            ),
            suggested=(
                "Regenerate the lists. Pick one spelling variant — the house convention is not "
                "yet set (CLAUDE.md §9), so this is flagged as an inconsistency rather than a "
                "preference."
            ),
        ),
    ]

    demo_rewrite = DemonstrationRewrite(
        section_title="§7.1 Conclusions",
        intro_note=(
            "One section only, chosen because it carries the highest-severity structural fault. "
            "A demonstration of the form the guide asks for, not a proposed replacement text — "
            "the author owns the wording and the engineering judgement in it."
        ),
        as_written_title="AS WRITTEN (PRINTED PAGE 28, ABRIDGED)",
        as_written_text=(
            "The design and operation of 132 equipment items were evaluated. This evaluation "
            "covered the following: 1. No asset is classified as Criticality 1 (RUL ≤ 0 yrs) … "
            "3. 1 static component 35-V-101 shell is classified as Criticality 2 "
            "(6 < RUL ≤ 14 yrs), and 16 static components are classified as Criticality 3 "
            "(6 < RUL ≤ 14 yrs) 4. The summary of 202 7 directly impacted by post tie-in "
            "condition criticality classification for component level as shown in Table 6-3 "
            "is listed below: a. Criticality 1 = 0 component b. Criticality 2 = 0 component "
            "c. Criticality 3 = 2 components d. Criticality 4 = 25 components. The summary "
            "of 2027 directly impacted … ALE priority classification … as shown in Figure 6-2 "
            "is listed below: a. Priority 1 = 0 component b. Priority 2 = 2 components … "
            "5. [the same structure repeated for indirectly impacted] … 6. [the same structure "
            "repeated for not impacted] …"
        ),
        faults_summary=(
            "Four faults against Ch 11: the lead-in says the list is what the evaluation covered, "
            "but the list is findings; items 4, 5 and 6 are the §6 result tables restated; six "
            "table and figure references appear inside the conclusions; and item 3 states a "
            "definition the rest of the document contradicts."
        ),
        demonstration_title="DEMONSTRATION — THE SAME CONTENT AS CONCLUSIONS",
        demonstration_items=[
            (
                "1. No component of the 175 assessed has exhausted its remaining wall thickness, "
                "and none is classified as Criticality 1."
            ),
            (
                "2. 158 components, 90 per cent of those assessed, have more than fourteen years "
                "of remaining life and are projected to reach the 2040 extension target on current "
                "corrosion rates."
            ),
            (
                "3. Sixteen components are classified as Criticality 3, with between six and "
                "fourteen years of remaining life, and require inspection to verify current wall "
                "thickness."
            ),
            (
                "4. One component, 35-V-101 SHELL, is classified as Criticality 2 with six years "
                "or less of remaining life, and is therefore the only component not projected to "
                "reach the 2040 target without intervention."
            ),
            (
                "5. Twenty-one components require inspection before the end of 2027, of which "
                "sixteen are driven by RBI risk rather than by remaining life."
            ),
            (
                "6. The remaining 154 components can be managed under the existing PCMS-RBI "
                "programme without additional intervention."
            ),
            (
                "7. Remaining life alone is not a sufficient basis for setting inspection "
                "priority, because sixteen of the twenty-one near-term inspections arise from "
                "risk category rather than from remaining life."
            ),
            (
                "8. Inspection priority for this plant should therefore be set from both RUL "
                "criticality and RBI risk category, as applied in Table 3-1."
            ),
        ],
        conclusion_summary=(
            "Eight numbered single sentences. No table reference, no figure reference, no restated "
            "result table. The per-population counts are not lost — they remain in §6 and in the "
            "Executive Summary, where the guide permits them. Note that conclusion 4 now states "
            "the exception the original buried, and conclusions 7 and 8 preserve the report's "
            "most useful insight, which the original placed last."
        ),
    )

    what_it_does_well = [
        (
            "Every count in the document reconciles. I traced the whole chain by hand: "
            "Table 2-1 (121 + 54 = 175 components, 94 + 38 = 132 equipment), Table 2-2 "
            "(27 + 112 + 36 = 175), Tables 1-1 to 1-3 (Criticality 4: 25 + 97 + 36 = 158; "
            "Criticality 3: 2 + 14 + 0 = 16; Criticality 2: 1), Table 6-2 (rows summing to 1, "
            "16 and 158), and the Criticality 4 risk split (34 + 37 + 71 + 16 = 158). Every one "
            "is exact. Not one of the previous three reports achieved this."
        ),
        (
            "The priority counts can be re-derived independently, and they hold. Applying the "
            "Table 3-1 rules to the Table 6-2 matrix gives P1 = 0, P2 = 0 + 1 + 4 + 16 = 21, "
            "P3 = 0 + 5 + 7 + 71 = 83, P4 = 37, P5 = 34, totalling 175 — matching the Executive "
            "Summary and §7.1 exactly. A reviewer can audit the entire prioritisation from two "
            "tables. That is the highest form of traceability in this sample and it should be "
            "the model for the rest of the programme."
        ),
        (
            "Table 3-1 and Table 3-2 together are the best single artefact reviewed so far. "
            "A four-by-four matrix maps RUL criticality against RBI risk to a priority, and a "
            "companion table gives the recommended activity and the inspection date for each "
            "priority. It converts engineering judgement into a rule that a third party can "
            "apply, audit and disagree with specifically. Put this in the template."
        ),
        (
            "The priority rules are stated twice — as prose in §3 and as the matrix in Table 3-1 "
            "— and the two agree. I checked all twenty cells against the five prose paragraphs and "
            "found no discrepancy. Stating a rule in two forms is how you make it reviewable."
        ),
        (
            "§3.1 states the tie-breaking rules explicitly: most severe criticality governs the "
            "equipment rating, then governing tmin, then the corrosion-rate hierarchy, then shell "
            "before head. Most assessment reports leave this implicit and become unauditable as a "
            "result."
        ),
        (
            "§4 gives fifteen numbered assumptions, including the ones authors usually leave "
            "unsaid — that the corrosion rate is held constant from 2027 to 2040, that PCMS "
            "data is assumed accurate, and that remaining life excludes cracking and mechanical "
            "damage mechanisms. Item 3 names the Indonesian ministerial decision behind the "
            ">20-year reporting cap. Naming the regulation behind a reporting convention is "
            "unusually good practice."
        ),
        (
            "The note beneath Table 3-2 pre-empts the reader's obvious confusion in one sentence: "
            "the RUL is calculated from the last inspection date against a 2026 baseline, while "
            "criticality and priority are assessed at the 2027 post tie-in datum. That single "
            "sentence prevents a reader spending ten minutes reconciling “RUL 2026” against "
            "“2027 ALE priority”."
        ),
        (
            "§2.4 does not merely list what is excluded — it names the programme that picks each "
            "exclusion up, from ASME PCC-1 bolting through to the Suban pipeline ILI study. That "
            "is how a limitation should be written: the reader learns both what is missing and "
            "where it is covered."
        ),
        (
            "The recommendations carry dates. “Before the end of 2027”, “every 3 – 5 years”, "
            "“by end-2027”, “half RUL or RBI recommendation, whichever is earlier”. This is the "
            "best date discipline in the sample; adding an owner column is all that stands "
            "between §7.2 and a pass on baseline measure 4."
        ),
    ]

    limits_of_review = [
        (
            "This is a technical writing review. I have not assessed whether the RUL calculations "
            "are correct, whether the corrosion rates are appropriate, whether the priority matrix "
            "reflects sound integrity practice, or whether the plant can safely operate to 2040. "
            "If the engineering is wrong, a well-structured report will still pass this review."
        ),
        (
            "No figure in this report is asserted to be incorrect. Blocker 1 is a stated "
            "definition contradicting the document's own definition tables, quoted from both. "
            "Where the Executive Summary's 0.65 mm/year differs from Appendix C's "
            "0.657657658 mm/year, the finding is the absence of a stated rounding convention, "
            "not that either value is wrong."
        ),
        (
            "Page numbers are the printed page numbers in the document footer, not PDF positions; "
            "the offset is one. Twenty-one pages carry no printed number at all and are cited by "
            "their appendix instead."
        ),
        (
            "The numeric sweep script mis-located the Executive Summary on this document and "
            "returned the table of contents instead — the numeric claims it reported were section "
            "numbers. The summary sweep was therefore done by hand. The script also reported "
            "90.29% as untraceable; on reading, it is 158 of 175, both of which appear in the "
            "document, so I have recorded it as a missing stated basis rather than as a blocker. "
            "Both failures are recorded against the tools in CLAUDE.md §8b."
        ),
        (
            "The scripted reference-drift check again returned nothing comparable, because the "
            "captions carry no bracketed citations — the third report in a row. The front-list "
            "page drift in finding 1 was found by a purpose-written check, not by ref_drift.py, "
            "and it found 15 of 28 where reading found 3. This is the same ratio recorded on "
            "report 01 and it is now a repeated result rather than a one-off."
        ),
        (
            "Scores are one reviewer's judgement. Where a second assessor scores the same "
            "document, the items they disagree on are the items needing a house interpretation — "
            "I would expect disagreement on IV.5 and IV.6, since this report type may not "
            "require a discussion chapter at all, and on whether finding 2 is a blocker under your "
            "document-control rules."
        ),
        (
            "The report was supplied with client name, originator, plant name, document number and "
            "three named individuals intact. Anonymise before it becomes training material."
        ),
        (
            "This review is an aid to the named reviewer on the cover, not a substitute for them. "
            "It is not an approval, a sign-off, or a QA release."
        ),
    ]

    return AssessmentData(
        title="Review of Asset Life Extension Study, Grissik Plant Static Equipment",
        subtitle=(
            "Scored against the document review checklist of Budinski, "
            "Engineers' Guide to Technical Writing (2001), Appendix 12"
        ),
        header_title="DOCUMENT REVIEW · ENGINEERING",
        running_header=(
            "Review of ALE Study Grissik Static Equipment, "
            "Doc. ID-N-CG-MM1-DSR-PL-00-3001 Rev A — writing review only"
        ),
        metadata=meta,
        summary_judgement=summary_judgement,
        bottom_line=bottom_line,
        baseline_measures=scorecard.baseline_measures,  # type: ignore[arg-type]
        blockers=blockers,
        major_findings=major_findings,
        language_findings=language_findings,
        demonstration_rewrite=demo_rewrite,
        scorecard=scorecard,
        what_it_does_well=what_it_does_well,
        limits_of_review=limits_of_review,
        review_score_string=scorecard.review_score_string,
    )
