"""
Extraction Schema Models
========================
Defines the normalized artifact format produced by the extraction service.
"""

from uuid import UUID

from pydantic import Field

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
