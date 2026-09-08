"""
Document Layout Inspector Service
=================================
Diagnostics for layout anomalies, typography misclassifications,
page-continuity breaks, unintended whitespace, and uncontrolled pages.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from unicodedata import normalize

from schemas.extraction import (
    CoordinateContract,
    LayoutAnomaly,
    PageBlock,
    PageMetric,
    PDFPage,
)

logger = logging.getLogger(__name__)

# Terminal punctuation patterns (sentences properly ended)
_TERMINAL_PUNCTUATION_PATTERN = re.compile(r'[.!?:]\s*[\'")\]]*$')

# Dangling conjunctions / prepositions at line/page ends
_DANGLING_CONJUNCTION_PATTERN = re.compile(
    r"\b(and|or|but|nor|so|yet|with|as|to|for|of|in|on|at|by|from|the|a|an)\s*$",
    re.IGNORECASE,
)

# Trailing punctuation indicating continuation (comma, dash, ellipsis)
_CONTINUATION_PUNCTUATION_PATTERN = re.compile(r"[,;–—-]\s*$")

# Narrative descriptive phrases that should NOT be styled as headings/outline headers
_NARRATIVE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:"
    r"based\s+on|"
    r"referring\s+to|"
    r"according\s+to|"
    r"with\s+reference\s+to|"
    r"in\s+accordance\s+with|"
    r"as\s+(?:shown|described|discussed|noted|stated|indicated|presented|defined)\s+in|"
    r"pursuant\s+to|"
    r"following\s+(?:the|this)|"
    r"in\s+order\s+to|"
    r"please\s+note\s+that|"
    r"note\s+that|"
    r"in\s+regard\s+to|"
    r"with\s+regard\s+to"
    r")\b",
    re.IGNORECASE,
)

# Page number patterns in footers/headers
_PAGE_NUMBER_PATTERN = re.compile(
    r"\b(?:page\s+\d+(\s+of\s+\d+)?|\d+\s*/\s*\d+|[ivxlcdm]+)\b",
    re.IGNORECASE,
)

# Document identification number patterns (e.g., ID-N-CG-MM1-DSR-PL-00-3001, DOC-12345)
_DOC_NUMBER_PATTERN = re.compile(
    r"\b(?:[A-Z0-9]{2,}-[A-Z0-9\-_/]{4,}|DOC(?:NO)?[:\s#]+[A-Z0-9\-_/]+)\b",
    re.IGNORECASE,
)

# Footer / page-label exclusion pattern for identifying body text
_FOOTER_EXCLUSION_PATTERN = re.compile(
    r"^\s*(?:page\s+\d+(\s+of\s+\d+)?|\d+|[ivxlcdm]+|[A-Z0-9\-_/]{6,})\s*$",
    re.IGNORECASE,
)


def _normalize_title(text: str) -> str:
    """Normalize a section heading or caption title for robust comparison."""
    norm = normalize("NFKC", text).strip().lower()
    norm = re.sub(r"[\.\s_–—]+$", "", norm)
    norm = re.sub(r"\s+", " ", norm)
    return norm


def _normalize_pages(doc_or_page: Any) -> list[Any]:
    """Helper to convert fitz.Document, fitz.Page, or list of pages into a list of fitz.Page."""
    if hasattr(doc_or_page, "page_count"):
        return [doc_or_page[i] for i in range(len(doc_or_page))]
    if isinstance(doc_or_page, (list, tuple)):
        return list(doc_or_page)
    return [doc_or_page]


class DocumentLayoutInspector:
    """
    Performs layout, typography, and page-continuity diagnostics on extracted document structures.
    """

    def detect_cross_page_sentence_breaks(
        self, page_blocks: list[PageBlock]
    ) -> list[LayoutAnomaly]:
        """
        Check for sentences broken across page boundaries where page N ends without
        terminal punctuation (e.g., ending with 'and', 'or', comma) and continues onto page N+1.
        """
        anomalies: list[LayoutAnomaly] = []
        if not page_blocks:
            return anomalies

        # Group valid text blocks by page_index
        blocks_by_page: dict[int, list[PageBlock]] = {}
        for block in page_blocks:
            txt = block.text.strip()
            if not txt:
                continue
            blocks_by_page.setdefault(block.page_index, []).append(block)

        sorted_page_indices = sorted(blocks_by_page.keys())
        if len(sorted_page_indices) < 2:
            return anomalies

        for i in range(len(sorted_page_indices) - 1):
            curr_page = sorted_page_indices[i]
            next_page = sorted_page_indices[i + 1]

            curr_blocks = blocks_by_page[curr_page]
            next_blocks = blocks_by_page[next_page]

            # Sort blocks by vertical position if coordinates exist
            curr_sorted = sorted(
                curr_blocks,
                key=lambda b: b.bbox.y1 if b.bbox else 0.0,
            )
            next_sorted = sorted(
                next_blocks,
                key=lambda b: b.bbox.y0 if b.bbox else 0.0,
            )

            # Filter out running footers / page numbers from the bottom of page N
            last_body_block: PageBlock | None = None
            for b in reversed(curr_sorted):
                t = b.text.strip()
                if not _FOOTER_EXCLUSION_PATTERN.match(t):
                    last_body_block = b
                    break

            if last_body_block is None:
                continue

            last_text = last_body_block.text.strip()

            # Filter out running headers / doc numbers from the top of page N+1
            first_body_block: PageBlock | None = None
            for b in next_sorted:
                t = b.text.strip()
                if not _FOOTER_EXCLUSION_PATTERN.match(t):
                    first_body_block = b
                    break

            if first_body_block is None:
                continue

            first_text = first_body_block.text.strip()

            # Check if page N ends with a non-terminal token
            ends_with_conjunction = bool(_DANGLING_CONJUNCTION_PATTERN.search(last_text))
            ends_with_continuation_punct = bool(_CONTINUATION_PUNCTUATION_PATTERN.search(last_text))
            has_terminal_punct = bool(_TERMINAL_PUNCTUATION_PATTERN.search(last_text))

            is_cross_page_break = False
            reason = ""

            if ends_with_conjunction:
                is_cross_page_break = True
                match = _DANGLING_CONJUNCTION_PATTERN.search(last_text)
                conjunction = match.group(1) if match else "conjunction"
                reason = f"ends with conjunction '{conjunction}'"
            elif ends_with_continuation_punct:
                is_cross_page_break = True
                reason = "ends with non-terminal punctuation (comma/dash)"
            elif not has_terminal_punct:
                # If neither terminal punctuation nor conjunction, check if text continues
                # (e.g. starts with lowercase or continuation phrase on next page)
                if first_text and (first_text[0].islower() or not has_terminal_punct):
                    is_cross_page_break = True
                    reason = "lacks terminal punctuation and sentence continues"

            if is_cross_page_break:
                last_words = " ".join(last_text.split()[-6:])
                anomalies.append(
                    LayoutAnomaly(
                        anomaly_type="CROSS_PAGE_BREAK",
                        category="PAGE_CONTINUITY",
                        severity="WARNING",
                        page_index=curr_page,
                        description=(
                            f"Sentence break across page boundaries: page {curr_page} "
                            f"{reason} ('...{last_words}') and continues to page {next_page}."
                        ),
                        message=(
                            f"Cross-page sentence break on page {curr_page} "
                            f"continuing to page {next_page}"
                        ),
                        location=last_body_block.bbox,
                        bbox=last_body_block.bbox,
                        details={
                            "page_index": curr_page,
                            "next_page_index": next_page,
                            "last_text": last_text,
                            "continuation_text": first_text[:80],
                            "reason": reason,
                        },
                    )
                )

        return anomalies

    def detect_style_misclassification(self, page_blocks: list[PageBlock]) -> list[LayoutAnomaly]:
        """
        Detect text blocks that begin with narrative descriptive phrases
        (e.g., 'Based on...', 'Referring to...') but have bold font attributes
        or are registered as headings/outline headers.
        """
        anomalies: list[LayoutAnomaly] = []

        for block in page_blocks:
            text = block.text.strip()
            if not text:
                continue

            if not _NARRATIVE_PREFIX_PATTERN.match(text):
                continue

            # Check if block has bold typography or heading/outline classification
            is_bold = block.is_bold
            if not is_bold and block.font_name:
                font_lower = block.font_name.lower()
                is_bold = any(
                    kw in font_lower for kw in ["bold", "black", "heavy", "w7", "w8", "w9"]
                )

            has_misclassified_style = is_bold or block.is_heading or block.is_outline

            if has_misclassified_style:
                style_reasons = []
                if is_bold:
                    style_reasons.append("bold font attribute")
                if block.is_heading:
                    style_reasons.append("heading classification")
                if block.is_outline:
                    style_reasons.append("outline header")

                snippet = text[:60] + ("..." if len(text) > 60 else "")
                anomalies.append(
                    LayoutAnomaly(
                        anomaly_type="STYLE_MISCLASSIFICATION",
                        category="TYPOGRAPHY",
                        severity="WARNING",
                        page_index=block.page_index,
                        description=(
                            f"Descriptive narrative text misclassified as heading on page "
                            f"{block.page_index} (applied {', '.join(style_reasons)}): '{snippet}'"
                        ),
                        message=(
                            f"Style misclassification on page {block.page_index}: "
                            "narrative text formatted as heading"
                        ),
                        location=block.bbox,
                        bbox=block.bbox,
                        details={
                            "text": text,
                            "is_bold": block.is_bold,
                            "is_heading": block.is_heading,
                            "is_outline": block.is_outline,
                            "font_name": block.font_name,
                            "font_size": block.font_size,
                            "reasons": style_reasons,
                        },
                    )
                )

        return anomalies

    def detect_unintended_whitespace(
        self, page_metrics: list[PageMetric]
    ) -> list[LayoutAnomaly]:
        """
        Detect pages in the middle of a document with text utilization ratio < 25%
        (void or largely blank pages before transitioning to subsequent sections).
        """
        anomalies: list[LayoutAnomaly] = []
        if len(page_metrics) < 3:
            return anomalies

        sorted_metrics = sorted(page_metrics, key=lambda m: m.page_index)
        min_page = sorted_metrics[0].page_index
        max_page = sorted_metrics[-1].page_index

        for metric in sorted_metrics:
            # Exclude cover/first page and final/back page
            if metric.page_index <= min_page or metric.page_index >= max_page:
                continue

            ratio = metric.text_utilization_ratio
            if ratio > 1.0:
                ratio = ratio / 100.0

            if ratio < 0.25:
                percentage_str = f"{ratio * 100.0:.1f}%"
                anomalies.append(
                    LayoutAnomaly(
                        anomaly_type="UNINTENDED_WHITESPACE",
                        category="LAYOUT",
                        severity="HIGH",
                        page_index=metric.page_index,
                        description=(
                            f"Unintended whitespace: page {metric.page_index} in middle of "
                            f"document has low text utilization ({percentage_str} < 25.0%)."
                        ),
                        message=(
                            f"Page {metric.page_index} has unintended whitespace / void layout "
                            f"({percentage_str} utilization)"
                        ),
                        details={
                            "page_index": metric.page_index,
                            "text_utilization_ratio": ratio,
                            "threshold": 0.25,
                            "has_images": metric.has_images,
                            "has_tables": metric.has_tables,
                            "word_count": metric.word_count,
                        },
                    )
                )

        return anomalies

    def audit_uncontrolled_pages(
        self,
        pages: list[PDFPage],
        expected_doc_number: str | None = None,
    ) -> list[LayoutAnomaly]:
        """
        Verify that every page (both portrait and landscape) contains all 4 control elements:
        running header, running footer, page number, and document number.
        """
        anomalies: list[LayoutAnomaly] = []

        # Auto-detect canonical document number from early pages if not supplied
        if not expected_doc_number and pages:
            for p in pages[:5]:
                for text_source in (p.footer_text or "", p.header_text or "", p.raw_text or ""):
                    m = _DOC_NUMBER_PATTERN.search(text_source)
                    if m and len(m.group(0)) >= 10:
                        expected_doc_number = m.group(0)
                        break
                if expected_doc_number:
                    break

        for page in pages:
            is_landscape = (page.width > page.height) or (page.orientation.lower() == "landscape")
            orientation = "landscape" if is_landscape else "portrait"

            missing_elements: list[str] = []

            # 1. Running Header
            has_header = page.has_header or bool(page.header_text and page.header_text.strip())
            if not has_header and page.blocks:
                header_cutoff = page.height * 0.15
                has_header = any(
                    b.bbox and b.bbox.y0 <= header_cutoff and len(b.text.strip()) > 3
                    for b in page.blocks
                )
            if not has_header:
                missing_elements.append("running_header")

            # 2. Running Footer
            has_footer = page.has_footer or bool(page.footer_text and page.footer_text.strip())
            if not has_footer and page.blocks:
                footer_cutoff = page.height * 0.85
                has_footer = any(
                    b.bbox and b.bbox.y1 >= footer_cutoff and len(b.text.strip()) > 3
                    for b in page.blocks
                )
            if not has_footer:
                missing_elements.append("running_footer")

            # 3. Page Number
            has_page_num = page.has_page_number or (
                page.page_number is not None and str(page.page_number).strip() != ""
            )
            hf_text = f"{page.header_text or ''} {page.footer_text or ''}".strip()
            if not has_page_num:
                text_to_search = (
                    page.raw_text
                    or hf_text
                    or " ".join(b.text for b in page.blocks)
                )
                has_page_num = bool(_PAGE_NUMBER_PATTERN.search(text_to_search))
            if not has_page_num:
                missing_elements.append("page_number")

            # 4. Document Number
            if expected_doc_number:
                has_doc_num = (
                    expected_doc_number in (page.header_text or "")
                    or expected_doc_number in (page.footer_text or "")
                    or expected_doc_number in (page.raw_text or "")
                )
            else:
                has_doc_num = page.has_doc_number or bool(
                    page.doc_number and page.doc_number.strip()
                )
                if not has_doc_num:
                    text_to_search = (
                        page.raw_text
                        or hf_text
                        or " ".join(b.text for b in page.blocks)
                    )
                    has_doc_num = bool(_DOC_NUMBER_PATTERN.search(text_to_search))

            if not has_doc_num:
                missing_elements.append("document_number")

            if missing_elements:
                anomalies.append(
                    LayoutAnomaly(
                        anomaly_type="UNCONTROLLED_PAGE",
                        category="PAGE_INTEGRITY",
                        severity="HIGH",
                        page_index=page.page_index,
                        description=(
                            f"Uncontrolled page {page.page_index} ({orientation}): "
                            f"missing {', '.join(missing_elements)}."
                        ),
                        message=(
                            f"Page {page.page_index} ({orientation}) is uncontrolled: "
                            f"missing {', '.join(missing_elements)}"
                        ),
                        details={
                            "page_index": page.page_index,
                            "orientation": orientation,
                            "missing_elements": missing_elements,
                            "width": page.width,
                            "height": page.height,
                        },
                    )
                )

        return anomalies

    def validate_front_matter_navigation(
        self, toc_entries: list[Any], actual_positions: dict[str, Any]
    ) -> list[LayoutAnomaly]:
        """
        Check for page number drift between Table of Contents / Figures / Tables
        and the physical location of objects in the document.
        """
        anomalies: list[LayoutAnomaly] = []
        if not toc_entries or not actual_positions:
            return anomalies

        # Create normalized lookup index for actual positions
        normalized_actual: dict[str, Any] = {}
        for key, val in actual_positions.items():
            normalized_actual[_normalize_title(str(key))] = val

        for entry in toc_entries:
            title = ""
            ref_page: int | None = None
            location: CoordinateContract | None = None

            if isinstance(entry, dict):
                title = (
                    entry.get("normalized_title")
                    or entry.get("title")
                    or entry.get("raw_text")
                    or entry.get("label")
                    or ""
                )
                raw_page = (
                    entry.get("referenced_page_number")
                    or entry.get("referenced_page")
                    or entry.get("page")
                    or entry.get("referenced_page_label")
                )
                location = entry.get("location") or entry.get("bbox")
            else:
                title = (
                    getattr(entry, "normalized_title", None)
                    or getattr(entry, "title", None)
                    or getattr(entry, "raw_text", None)
                    or getattr(entry, "label", None)
                    or ""
                )
                raw_page = (
                    getattr(entry, "referenced_page_number", None)
                    or getattr(entry, "referenced_page", None)
                    or getattr(entry, "page", None)
                    or getattr(entry, "referenced_page_label", None)
                )
                location = getattr(entry, "location", None) or getattr(entry, "bbox", None)

            if raw_page is not None:
                try:
                    ref_page = int(str(raw_page).strip())
                except ValueError:
                    ref_page = None

            if not title or ref_page is None:
                continue

            norm_title = _normalize_title(title)
            actual_val = actual_positions.get(title) or normalized_actual.get(norm_title)

            # Try partial prefix matching if exact normalized key not found
            if actual_val is None:
                for k, v in normalized_actual.items():
                    if norm_title in k or k in norm_title:
                        actual_val = v
                        break

            if actual_val is None:
                continue

            actual_page: int | None = None
            if isinstance(actual_val, (int, float)):
                actual_page = int(actual_val)
            elif isinstance(actual_val, dict):
                p = (
                    actual_val.get("actual_page_index")
                    or actual_val.get("page")
                    or actual_val.get("page_index")
                    or actual_val.get("actual_page")
                    or actual_val.get("actual_page_number")
                )
                if p is not None:
                    actual_page = int(p)
            else:
                p = (
                    getattr(actual_val, "actual_page_index", None)
                    or getattr(actual_val, "page", None)
                    or getattr(actual_val, "page_index", None)
                    or getattr(actual_val, "actual_page", None)
                )
                if p is not None:
                    actual_page = int(p)

            if actual_page is not None and actual_page != ref_page:
                drift = actual_page - ref_page
                anomalies.append(
                    LayoutAnomaly(
                        anomaly_type="FRONT_MATTER_DRIFT",
                        category="NAVIGATION",
                        severity="HIGH",
                        page_index=ref_page,
                        description=(
                            f"Navigation drift for '{title}': listed on page {ref_page}, "
                            f"actual position is page {actual_page} (drift: {drift:+d} pages)."
                        ),
                        message=f"Navigation drift for '{title}' (drift: {drift:+d} pages)",
                        location=location,
                        bbox=location,
                        details={
                            "title": title,
                            "referenced_page": ref_page,
                            "actual_page": actual_page,
                            "drift": drift,
                        },
                    )
                )

        return anomalies

    # ── PyMuPDF (fitz) Extraction Helpers ─────────────────────────────────────

    def extract_page_blocks_from_fitz(self, doc_or_page: Any) -> list[PageBlock]:
        """
        Extract PageBlock models using coordinates and font dictionary from PyMuPDF.
        """
        page_blocks: list[PageBlock] = []
        pages = _normalize_pages(doc_or_page)

        for page in pages:
            page_index = getattr(page, "number", 0)
            rect = page.rect
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])

            for block in blocks:
                b_type = block.get("type", 0)
                if b_type != 0:  # non-text block
                    continue

                b_bbox = block.get("bbox", (0, 0, 0, 0))
                full_text_spans: list[str] = []
                primary_font = ""
                primary_size = 10.0
                is_bold = False
                is_italic = False

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        stext = span.get("text", "")
                        full_text_spans.append(stext)
                        font = span.get("font", "")
                        flags = span.get("flags", 0)
                        size = span.get("size", 10.0)

                        if not primary_font and font:
                            primary_font = font
                            primary_size = size

                        # PyMuPDF font flags: bit 4 (16) is bold, bit 1 (2) is italic
                        if (
                            (flags & 16 != 0)
                            or ("bold" in font.lower())
                            or ("black" in font.lower())
                        ):
                            is_bold = True
                        if (
                            (flags & 2 != 0)
                            or ("italic" in font.lower())
                            or ("oblique" in font.lower())
                        ):
                            is_italic = True

                block_text = "".join(full_text_spans).strip()
                if not block_text:
                    continue

                coord = CoordinateContract(
                    page_index=page_index,
                    x0=b_bbox[0],
                    y0=b_bbox[1],
                    x1=b_bbox[2],
                    y1=b_bbox[3],
                    page_width=rect.width,
                    page_height=rect.height,
                )

                page_blocks.append(
                    PageBlock(
                        page_index=page_index,
                        text=block_text,
                        bbox=coord,
                        font_name=primary_font,
                        font_size=primary_size,
                        is_bold=is_bold,
                        is_italic=is_italic,
                        is_heading=(is_bold and primary_size > 12.0),
                        is_outline=False,
                        block_type=b_type,
                        lines=block.get("lines"),
                    )
                )

        return page_blocks

    def calculate_page_metrics_from_fitz(self, doc_or_page: Any) -> list[PageMetric]:
        """
        Calculate page density and text utilization ratios from PyMuPDF.
        """
        metrics: list[PageMetric] = []
        pages = _normalize_pages(doc_or_page)

        for page in pages:
            page_index = getattr(page, "number", 0)
            rect = page.rect
            total_area = rect.width * rect.height
            if total_area <= 0:
                continue

            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])

            used_area = 0.0
            word_count = 0
            has_images = False

            for block in blocks:
                if block.get("type") == 1:
                    has_images = True
                    b = block.get("bbox", (0, 0, 0, 0))
                    used_area += max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
                elif block.get("type") == 0:
                    b = block.get("bbox", (0, 0, 0, 0))
                    used_area += max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            word_count += len(span.get("text", "").split())

            utilization_ratio = min(1.0, used_area / total_area) if total_area > 0 else 0.0

            metrics.append(
                PageMetric(
                    page_index=page_index,
                    text_utilization_ratio=utilization_ratio,
                    page_width=rect.width,
                    page_height=rect.height,
                    used_area=used_area,
                    total_area=total_area,
                    word_count=word_count,
                    has_images=has_images,
                    has_tables=False,
                )
            )

        return metrics

    def extract_pdf_pages_from_fitz(self, doc_or_page: Any) -> list[PDFPage]:
        """
        Extract PDFPage entities from a PyMuPDF Document for control element auditing.
        """
        pdf_pages: list[PDFPage] = []
        pages = _normalize_pages(doc_or_page)
        for page in pages:
            page_index = page.number
            rect = page.rect
            blocks = self.extract_page_blocks_from_fitz(page)
            raw_text = page.get_text()

            # Identify header (top 15%) and footer (bottom 15%)
            header_cutoff = rect.height * 0.15
            footer_cutoff = rect.height * 0.85

            header_parts = [b.text for b in blocks if b.bbox and b.bbox.y0 <= header_cutoff]
            footer_parts = [b.text for b in blocks if b.bbox and b.bbox.y1 >= footer_cutoff]

            header_text = " ".join(header_parts).strip() if header_parts else None
            footer_text = " ".join(footer_parts).strip() if footer_parts else None

            # Check for doc number and page number
            doc_num_match = (
                _DOC_NUMBER_PATTERN.search(header_text or "")
                or _DOC_NUMBER_PATTERN.search(footer_text or "")
                or _DOC_NUMBER_PATTERN.search(raw_text)
            )
            page_num_match = _PAGE_NUMBER_PATTERN.search(
                footer_text or ""
            ) or _PAGE_NUMBER_PATTERN.search(header_text or "")

            orientation = "landscape" if rect.width > rect.height else "portrait"

            pdf_pages.append(
                PDFPage(
                    page_index=page_index,
                    width=rect.width,
                    height=rect.height,
                    orientation=orientation,
                    blocks=blocks,
                    raw_text=raw_text,
                    header_text=header_text,
                    footer_text=footer_text,
                    page_number=page_num_match.group(0) if page_num_match else None,
                    doc_number=doc_num_match.group(0) if doc_num_match else None,
                    has_header=bool(header_text),
                    has_footer=bool(footer_text),
                    has_page_number=bool(page_num_match),
                    has_doc_number=bool(doc_num_match),
                )
            )

        return pdf_pages
