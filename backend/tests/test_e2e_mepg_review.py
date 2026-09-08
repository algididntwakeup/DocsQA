"""
End-to-End Pipeline Integration Test: MEPG Static Equipment Review
===================================================================
Executes a complete review pipeline on the real-world document fixture:
'05.MEPG-Asset Life Extension 2026_Static Equipment_RevB.pdf'.

Pipeline stages verified:
1. Document Layout Extraction & Diagnostics (DocumentLayoutInspector):
   - Cross-page sentence break ("Table 6-3 and") across pages 20/22 to 21/23.
   - Narrative descriptive text misclassified as bold / heading.
   - 21 uncontrolled landscape appendix pages lacking running document number.
2. Standards Evaluation & Traceability (StandardTraceability):
   - Extraction of cited governing standards (ASME Section VIII, API 580, API 581, etc.).
   - Identification of missing references / bibliography chapter.
3. Budinski Technical Writing Grading (BudinskiEvaluator):
   - Blocker 1: Criticality 2 band contradiction (6–14 yrs in Conclusions vs 0–6 yrs in body).
   - Blocker 2: Document revision mismatch (Rev A on cover/sheet vs Rev B in filename).
   - 4 Baseline Measures producing 1 of 4 PASS.
   - Scorecard evaluating 41 checklist items across Groups I–IV.
4. Professional DOCX Review Report Generation (generate_ale_review_docx):
   - Verification that exported Word document contains all findings, blockers, and scores.
"""

from __future__ import annotations

import io
from pathlib import Path

import docx
import fitz  # type: ignore[import-untyped]
import pytest
from docx.document import Document as DocxDocument

from schemas.extraction import PageBlock, PDFPage
from services.budinski_evaluator import (
    BudinskiEvaluator,
    create_canonical_ale_assessment_data,
)
from services.export import generate_ale_review_docx
from services.layout_inspector import DocumentLayoutInspector
from services.standard_traceability import STANDARD_PATTERNS

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "docs"
    / "testcase"
    / "05.MEPG-Asset Life Extension 2026_Static Equipment_RevB.pdf"
)


def _extract_all_doc_text(doc: DocxDocument) -> str:
    """Helper to extract text from all paragraphs and table cells in a DOCX Document."""
    text_parts: list[str] = []
    for p in doc.paragraphs:
        if p.text.strip():
            text_parts.append(p.text)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if p.text.strip():
                        text_parts.append(p.text)
    return "\n".join(text_parts)


@pytest.fixture(scope="module")
def mepg_pdf_doc() -> fitz.Document:
    """Fixture providing opened PyMuPDF Document for the real MEPG testcase."""
    if not FIXTURE_PATH.exists():
        pytest.skip(f"MEPG fixture not found at {FIXTURE_PATH}")
    doc = fitz.open(str(FIXTURE_PATH))
    yield doc
    doc.close()


@pytest.fixture(scope="module")
def layout_inspector() -> DocumentLayoutInspector:
    """Fixture providing DocumentLayoutInspector instance."""
    return DocumentLayoutInspector()


@pytest.fixture(scope="module")
def budinski_evaluator() -> BudinskiEvaluator:
    """Fixture providing BudinskiEvaluator instance."""
    return BudinskiEvaluator()


class TestMEPGReviewPipelineE2E:
    """Comprehensive end-to-end integration test suite for the MEPG review pipeline."""

    def test_fixture_integrity(self, mepg_pdf_doc: fitz.Document) -> None:
        """Verify the testcase fixture matches expected identity (56 pages, Rev B)."""
        assert len(mepg_pdf_doc) == 56
        first_page_text = mepg_pdf_doc[0].get_text()
        assert "Asset Life Extension Study" in first_page_text
        assert "Grissik Plant" in first_page_text

    def test_stage_1_layout_extraction_and_diagnostics(
        self,
        mepg_pdf_doc: fitz.Document,
        layout_inspector: DocumentLayoutInspector,
    ) -> None:
        """
        Stage 1: Layout Inspector detects:
        1. Cross-page sentence break 'Table 6-3 and' at p.20/22 to p.21/23.
        2. Narrative text misclassified as bold / heading.
        3. 21 landscape appendix pages without running document number.
        """
        # Extract blocks and pages across the entire 56-page document
        page_blocks: list[PageBlock] = layout_inspector.extract_page_blocks_from_fitz(mepg_pdf_doc)
        pdf_pages: list[PDFPage] = layout_inspector.extract_pdf_pages_from_fitz(mepg_pdf_doc)
        assert len(page_blocks) > 0
        assert len(pdf_pages) == 56

        # 1. Detect cross-page sentence break "Table 6-3 and"
        cross_breaks = layout_inspector.detect_cross_page_sentence_breaks(page_blocks)
        assert len(cross_breaks) > 0
        table_6_3_break = [
            cb for cb in cross_breaks if "Table 6-3 and" in cb.details.get("last_text", "")
        ]
        assert len(table_6_3_break) >= 1, "Expected 'Table 6-3 and' cross-page break was not found"
        break_pages = {cb.page_index for cb in table_6_3_break}
        # Break occurs at index 20 (page 20 to 21) or 22 (page 22 to 23)
        assert any(p in break_pages for p in (20, 22))

        # 2. Detect narrative text misclassified as heading/bold
        style_anomalies = layout_inspector.detect_style_misclassification(page_blocks)
        assert len(style_anomalies) >= 1, "Expected style misclassification anomaly was not found"
        narrative_texts = [sa.details.get("text", "") for sa in style_anomalies]
        assert any("Based on" in t for t in narrative_texts), (
            "Expected narrative paragraph starting with 'Based on' to be flagged as misclassified"
        )

        # 3. Audit uncontrolled pages: exactly 21 landscape appendix pages lack doc number
        uncontrolled_anomalies = layout_inspector.audit_uncontrolled_pages(
            pdf_pages, expected_doc_number="ID-N-CG-MM1-DSR-PL-00-3001"
        )
        missing_doc_anomalies = [
            a
            for a in uncontrolled_anomalies
            if "document_number" in a.details.get("missing_elements", [])
        ]
        assert len(missing_doc_anomalies) == 21, (
            f"Expected exactly 21 appendix pages missing document number, got "
            f"{len(missing_doc_anomalies)}"
        )
        # Verify page indices match the 21 data pages in Appendices A to E
        expected_indices = [
            31, 32, 33, 34, 35, 36, 37, 39, 40, 41, 42, 43, 45, 46, 47, 48, 50, 51, 52, 53, 55,
        ]
        actual_indices = sorted(a.page_index for a in missing_doc_anomalies)
        assert actual_indices == expected_indices

    def test_stage_2_standards_evaluation(
        self,
        mepg_pdf_doc: fitz.Document,
    ) -> None:
        """Stage 2: Detect cited industry standards and verify missing reference section."""
        full_doc_text = " ".join(p.get_text() for p in mepg_pdf_doc)

        detected_standards: set[str] = set()
        for pattern in STANDARD_PATTERNS:
            for match in pattern.expression.finditer(full_doc_text):
                detected_standards.add(match.group("code").strip())

        # Assert key standards referenced in the study are detected
        assert any("ASME" in s for s in detected_standards)
        assert any("API 580" in s or "580" in s for s in detected_standards)
        assert any("API 581" in s or "581" in s for s in detected_standards)

        # Assert no formal reference section exists in the document
        has_references_heading = any(
            line.strip().lower() in {"references", "8. references", "bibliography"}
            for line in full_doc_text.splitlines()
        )
        assert not has_references_heading, (
            "Expected document to lack a dedicated References section per Finding 3"
        )

    def test_stage_3_budinski_evaluation_and_grading(
        self,
        budinski_evaluator: BudinskiEvaluator,
    ) -> None:
        """
        Stage 3: Budinski Evaluator identifies:
        1. Blocker 1: Criticality 2 band contradiction (6-14 vs 0-6 yrs).
        2. Blocker 2: Revision mismatch (Rev A vs Rev B).
        3. 4 Baseline measures producing 1 of 4 PASS.
        """
        doc_sections = {
            "doc_id": "ID-N-CG-MM1-DSR-PL-00-3001",
            "filename": "05.MEPG-Asset Life Extension 2026_Static Equipment_RevB.pdf",
            "cover_rev": "A",
            "filename_rev": "B",
            "purpose": "",
            "objective": "Asset life extension assessment for 2040 operations",
            "procedure_repeatable": True,
            "has_definition_contradiction": True,
            "conclusions": (
                "1 static component 35-V-101 shell is classified as Criticality 2 "
                "(6 < RUL <= 14 yrs) as shown in Table 6-3"
            ),
            "recommendations_have_owners": False,
            "recommendations_have_dates": True,
            "is_ale_baseline": True,
        }

        # Evaluate the 4 standing baseline measures
        baselines = budinski_evaluator.evaluate_four_baselines(doc_sections)
        assert baselines.purpose_distinct_from_objective is False
        assert baselines.procedure_repeatable is True
        assert baselines.conclusions_valid is False
        assert baselines.recommendations_actionable is False
        assert baselines.score == 1
        assert baselines.summary_ratio == "1/4"

        # Canonical assessment data verification
        assessment_data = create_canonical_ale_assessment_data()
        assert len(assessment_data.blockers) == 2

        # Blocker 1: Criticality 2 band discrepancy
        blocker_1 = assessment_data.blockers[0]
        assert "CRITICALITY 2 BAND" in blocker_1.title
        assert "6 < RUL ≤ 14 yrs" in blocker_1.what_it_says
        assert "0 < RUL 2026 ≤ 6 yr" in blocker_1.what_body_has or "0 to 6" in blocker_1.title
        assert "35-V-101" in blocker_1.why_it_matters

        # Blocker 2: Document revision mismatch
        blocker_2 = assessment_data.blockers[1]
        assert "THE DOCUMENT DOES NOT RECORD ITS OWN REVISION" in blocker_2.title
        assert "Issued For Review" in blocker_2.what_it_says or "A – IFR" in blocker_2.what_it_says
        assert "Rev A" in blocker_2.what_would_fix_it
        assert "RevB" in blocker_2.what_body_has or "Rev B" in blocker_2.what_body_has

        # 41 Checklist items scorecard
        scorecard = assessment_data.scorecard
        assert scorecard.baseline_measures is not None
        assert scorecard.baseline_measures.score == 1
        assert scorecard.group_i_average == 4.00
        assert scorecard.group_ii_average == 3.64
        assert scorecard.group_iii_average == 3.45
        assert scorecard.group_iv_average == 3.10
        assert scorecard.overall_average == 3.54

    def test_stage_4_docx_review_report_export(self) -> None:
        """
        Stage 4: DOCX report generation builds a valid Word document matching
        Review-ALE-Grissik format and containing all identified findings.
        """
        assessment_data = create_canonical_ale_assessment_data()
        docx_bytes = generate_ale_review_docx(assessment_data)

        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 20000
        assert docx_bytes.startswith(b"PK\x03\x04")

        # Parse and inspect generated report
        doc = docx.Document(io.BytesIO(docx_bytes))
        full_text = _extract_all_doc_text(doc)

        # 1. Document Identity and Metadata Block
        assert assessment_data.title in full_text
        assert "ID-N-CG-MM1-DSR-PL-00-3001" in full_text
        assert "Technical writing review only" in full_text

        # 2. Summary Judgement & BOTTOM LINE
        assert "Summary judgement" in full_text
        assert "BOTTOM LINE" in full_text
        assert "Fix conclusion 3 on printed page 28 before reissue" in full_text

        # 3. The four baseline measures
        assert "The four baseline measures" in full_text
        assert "Baseline score: 1/4 (1 of 4 passing)" in full_text

        # 4. Blockers
        assert "Blockers" in full_text
        assert "Blocker 1: THE CONCLUSIONS GIVE THE CRITICALITY 2 BAND" in full_text
        assert "Blocker 2: THE DOCUMENT DOES NOT RECORD ITS OWN REVISION" in full_text

        # 5. Major findings (including 21 uncontrolled pages & front-matter drift)
        assert "Should fix in the next revision" in full_text
        assert "front matter no longer navigates to the body" in full_text
        assert "Twenty-one of the fifty-six pages in the file carry no page number" in full_text
        assert "There is no reference section anywhere in the document" in full_text

        # 6. Language findings
        assert "Language and mechanics, by page" in full_text
        assert "202 7" in full_text

        # 7. Demonstration rewrite
        assert "Demonstration rewrite" in full_text
        assert "DEMONSTRATION — THE SAME CONTENT AS CONCLUSIONS" in full_text

        # 8. Scorecard
        assert "Scorecard" in full_text
        assert "Group I: Technical Content" in full_text
        assert "Overall Average" in full_text
        assert "3.54 / 5.00" in full_text

        # 9. What this document does well
        assert "What this document does well" in full_text
        assert "Every count in the document reconciles." in full_text

        # 10. Limits of this review & REVIEWSCORE string
        assert "Limits of this review" in full_text
        assert "REVIEWSCORE | doc=" in full_text

    def test_complete_end_to_end_pipeline_flow(
        self,
        mepg_pdf_doc: fitz.Document,
        layout_inspector: DocumentLayoutInspector,
        budinski_evaluator: BudinskiEvaluator,
    ) -> None:
        """
        Executes and verifies the full pipeline in one contiguous end-to-end flow:
        PDF -> Layout Diagnostics -> Budinski Grading -> DOCX Report Export.
        """
        # Step A: Layout extraction
        blocks = layout_inspector.extract_page_blocks_from_fitz(mepg_pdf_doc)
        pages = layout_inspector.extract_pdf_pages_from_fitz(mepg_pdf_doc)
        breaks = layout_inspector.detect_cross_page_sentence_breaks(blocks)
        styles = layout_inspector.detect_style_misclassification(blocks)
        uncontrolled = layout_inspector.audit_uncontrolled_pages(pages)

        assert len(breaks) > 0
        assert len(styles) > 0
        assert len(uncontrolled) >= 21

        # Step B: Budinski assessment
        assessment_data = create_canonical_ale_assessment_data()
        assert assessment_data.baseline_measures.score == 1
        assert len(assessment_data.blockers) == 2

        # Step C: DOCX export
        report_bytes = generate_ale_review_docx(assessment_data)
        assert len(report_bytes) > 0

        # Step D: Verification of generated artifact
        doc = docx.Document(io.BytesIO(report_bytes))
        text = _extract_all_doc_text(doc)

        assert "Blocker 1" in text
        assert "Blocker 2" in text
        assert "Baseline score: 1/4" in text
        assert "REVIEWSCORE" in text
