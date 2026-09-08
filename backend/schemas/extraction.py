"""
Extraction Schema Models
========================
Defines the normalized artifact format produced by the extraction service.
"""

from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from schemas.base import ApiModel


class CoordinateContract(ApiModel):
    """
    Canonical bounding box coordinate contract.
    Coordinate system is top-left in points (1/72 inch).
    """

    page_index: int = Field(ge=0, description="0-based index of the canonical PDF page.")
    x0: float = Field(description="Left coordinate (points).")
    y0: float = Field(description="Top coordinate (points).")
    x1: float = Field(description="Right coordinate (points).")
    y1: float = Field(description="Bottom coordinate (points).")
    page_width: float = Field(description="Width of the page in points.")
    page_height: float = Field(description="Height of the page in points.")


class TextSpan(ApiModel):
    """
    A contiguous span of text extracted from the document.
    """

    text: str
    bbox: CoordinateContract


class Heading(ApiModel):
    """
    A section heading extracted from the document.
    """

    text: str
    level: int = Field(ge=1, description="Heading level (e.g., 1 for H1).")
    bbox: CoordinateContract


class TableCell(ApiModel):
    """
    A single cell within a table.
    """

    text: str
    row_index: int = Field(ge=0)
    col_index: int = Field(ge=0)
    row_span: int = Field(default=1, ge=1)
    col_span: int = Field(default=1, ge=1)
    bbox: CoordinateContract | None = None


class Table(ApiModel):
    """
    An extracted data table.
    """

    cells: list[TableCell]
    bbox: CoordinateContract | None = None


class PageMetadata(ApiModel):
    """
    Metadata for a single canonical PDF page.
    """

    page_index: int = Field(ge=0)
    width: float
    height: float
    page_label: str | None = Field(
        default=None,
        description="Human-facing page label (e.g., 'iv' or '4').",
    )


class PageBlock(ApiModel):
    """
    A structural block on a document page with geometry and font characteristics.
    """

    page_index: int = Field(ge=0, description="0-based index of the page.")
    text: str = Field(description="Extracted textual content of the block.")
    bbox: CoordinateContract | None = Field(default=None, description="Bounding box on the page.")
    font_name: str | None = Field(default=None, description="Primary font name.")
    font_size: float | None = Field(default=None, description="Primary font size in points.")
    is_bold: bool = Field(default=False, description="True if text has bold attribute.")
    is_italic: bool = Field(default=False, description="True if text has italic attribute.")
    is_heading: bool = Field(default=False, description="True if classified as a section heading.")
    is_outline: bool = Field(default=False, description="True if listed in outline/bookmarks.")
    block_type: int | str = Field(default=0, description="PyMuPDF block type (0=text, 1=image).")
    lines: list[dict[str, Any]] | None = Field(
        default=None,
        description="Detailed line and span dictionary.",
    )


class PageMetric(ApiModel):
    """
    Utilization and density metrics for a document page.
    """

    page_index: int = Field(ge=0, description="0-based index of the page.")
    text_utilization_ratio: float = Field(
        description="Ratio of page surface utilized by text (0.0 to 1.0, or 0.0 to 100.0%).",
    )
    page_width: float = Field(default=0.0, ge=0.0)
    page_height: float = Field(default=0.0, ge=0.0)
    used_area: float = Field(default=0.0, ge=0.0)
    total_area: float = Field(default=0.0, ge=0.0)
    word_count: int = Field(default=0, ge=0)
    has_images: bool = Field(default=False)
    has_tables: bool = Field(default=False)


class PDFPage(ApiModel):
    """
    Page entity used to verify running control headers, footers, and geometry.
    """

    page_index: int = Field(ge=0, description="0-based index of the page.")
    width: float = Field(gt=0, description="Page width in points.")
    height: float = Field(gt=0, description="Page height in points.")
    orientation: str = Field(default="portrait", description="'portrait' or 'landscape'.")
    blocks: list[PageBlock] = Field(
        default_factory=list, description="Blocks belonging to this page."
    )
    raw_text: str = Field(default="", description="Full raw text of the page.")
    header_text: str | None = Field(default=None, description="Running header text if identified.")
    footer_text: str | None = Field(default=None, description="Running footer text if identified.")
    page_number: str | int | None = Field(
        default=None, description="Extracted page number label or value."
    )
    doc_number: str | None = Field(
        default=None, description="Extracted document identification number."
    )
    has_header: bool = Field(default=False, description="Whether running header is present.")
    has_footer: bool = Field(default=False, description="Whether running footer is present.")
    has_page_number: bool = Field(default=False, description="Whether page number is present.")
    has_doc_number: bool = Field(default=False, description="Whether document number is present.")


class LayoutAnomaly(ApiModel):
    """
    Diagnostic anomaly detected during layout, typography, and page-continuity inspection.
    """

    anomaly_type: str = Field(
        description=(
            "Category of anomaly (e.g. CROSS_PAGE_BREAK, STYLE_MISCLASSIFICATION, "
            "UNINTENDED_WHITESPACE, UNCONTROLLED_PAGE, FRONT_MATTER_DRIFT)."
        ),
    )
    category: str = Field(default="LAYOUT", description="High-level category.")
    severity: str = Field(
        default="WARNING",
        description="Severity label: INFO, LOW, MEDIUM, HIGH, CRITICAL.",
    )
    page_index: int = Field(
        ge=0, description="0-based index of the page where the anomaly was detected."
    )
    description: str = Field(default="", description="Detailed human-readable explanation.")
    message: str = Field(default="", description="Concise diagnostic message.")
    location: CoordinateContract | None = Field(
        default=None, description="Primary bounding box location."
    )
    bbox: CoordinateContract | None = Field(
        default=None, description="Alias for location bounding box."
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Diagnostic payload and context."
    )

    @model_validator(mode="before")
    @classmethod
    def sync_message_and_location(cls, data: Any) -> Any:
        if isinstance(data, dict):
            desc = data.get("description", "")
            msg = data.get("message", "")
            if not desc and msg:
                data["description"] = msg
            elif not msg and desc:
                data["message"] = desc

            loc = data.get("location")
            bbox = data.get("bbox")
            if loc is None and bbox is not None:
                data["location"] = bbox
            elif bbox is None and loc is not None:
                data["bbox"] = loc
        return data


class ExtractionArtifact(ApiModel):
    """
    The complete, normalized artifact produced by an extraction pipeline stage.
    """

    schema_version: str = Field(default="1.0")
    document_id: UUID
    pages: list[PageMetadata] = Field(default_factory=list)
    spans: list[TextSpan] = Field(default_factory=list)
    headings: list[Heading] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    warnings: list[str] = Field(
        default_factory=list,
        description="Extraction warnings, e.g., missing fonts or damaged structures.",
    )
