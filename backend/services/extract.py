"""
Text & Layout Extraction Service
=================================
Extracts raw text, layout metadata, table structures (bounding boxes, cell grid),
page anchors, and font metadata from PDF (PyMuPDF) and DOCX (python-docx).

Pipeline stage 0 — shared by both Linguistic and Traceability branches.
"""

import subprocess
import tempfile
import os
from pathlib import Path
from uuid import UUID
from typing import Optional
import logging

from schemas.extraction import (
    ExtractionArtifact, PageMetadata, TextSpan, CoordinateContract,
    Table, TableCell, Heading
)

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts text, headings, and tables from PDF files with canonical coordinates."""
    
    def extract(self, file_path: Path, document_id: UUID) -> ExtractionArtifact:
        artifact = ExtractionArtifact(document_id=document_id)
        
        try:
            import fitz
            doc = fitz.open(file_path)
        except Exception as e:
            artifact.warnings.append(f"Failed to open PDF: {str(e)}")
            return artifact

        for page_index in range(len(doc)):
            page = doc[page_index]
            rect = page.rect
            page_meta = PageMetadata(
                page_index=page_index,
                width=rect.width,
                height=rect.height
            )
            artifact.pages.append(page_meta)
            
            # Extract text blocks
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") == 0:  # text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text:
                                continue
                                
                            bbox = CoordinateContract(
                                page_index=page_index,
                                x0=span["bbox"][0],
                                y0=span["bbox"][1],
                                x1=span["bbox"][2],
                                y1=span["bbox"][3],
                                page_width=rect.width,
                                page_height=rect.height
                            )
                            
                            font_name = span.get("font", "")
                            font_size = span.get("size", 10)
                            is_bold = "Bold" in font_name or "Black" in font_name
                            
                            if is_bold and font_size > 12:
                                artifact.headings.append(Heading(
                                    text=text,
                                    level=1 if font_size > 16 else 2,
                                    bbox=bbox
                                ))
                            else:
                                artifact.spans.append(TextSpan(
                                    text=text,
                                    bbox=bbox
                                ))
                                
            # Extract tables using PyMuPDF's find_tables
            tables = page.find_tables()
            for t in tables:
                table_model = Table(cells=[])
                t_bbox = t.bbox
                table_model.bbox = CoordinateContract(
                    page_index=page_index,
                    x0=t_bbox[0],
                    y0=t_bbox[1],
                    x1=t_bbox[2],
                    y1=t_bbox[3],
                    page_width=rect.width,
                    page_height=rect.height
                )
                
                if t.cells:
                    for row_idx, row in enumerate(t.cells):
                        for col_idx, cell_rect in enumerate(row):
                            if cell_rect is None:
                                continue
                            
                            try:
                                cell_text = page.get_text("text", clip=cell_rect).strip()
                                if cell_text:
                                    cell_bbox = CoordinateContract(
                                        page_index=page_index,
                                        x0=cell_rect[0],
                                        y0=cell_rect[1],
                                        x1=cell_rect[2],
                                        y1=cell_rect[3],
                                        page_width=rect.width,
                                        page_height=rect.height
                                    )
                                    
                                    table_model.cells.append(TableCell(
                                        text=cell_text,
                                        row_index=row_idx,
                                        col_index=col_idx,
                                        bbox=cell_bbox
                                    ))
                            except Exception as e:
                                logger.warning(f"Error extracting table cell at row {row_idx}, col {col_idx}: {e}")
                                
                if table_model.cells:
                    artifact.tables.append(table_model)
        
        doc.close()
        return artifact


class DOCXExtractor:
    """
    Extracts structure from DOCX. Generates a canonical PDF via LibreOffice (soffice) 
    to obtain reliable bounding boxes.
    """
    
    def extract(self, file_path: Path, document_id: UUID) -> ExtractionArtifact:
        # First, attempt to convert to PDF for canonical coordinates
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Call headless LibreOffice
                result = subprocess.run([
                    "soffice", "--headless", "--convert-to", "pdf", 
                    str(file_path), "--outdir", temp_dir
                ], check=False, capture_output=True, text=True)
                
                if result.returncode == 0:
                    converted_pdf = Path(temp_dir) / file_path.with_suffix(".pdf").name
                    if converted_pdf.exists():
                        pdf_extractor = PDFExtractor()
                        artifact = pdf_extractor.extract(converted_pdf, document_id)
                        artifact.warnings.append("Converted from DOCX using headless LibreOffice for coordinate mapping.")
                        return artifact
                else:
                    logger.warning(f"soffice conversion failed: {result.stderr}")
        except FileNotFoundError:
            logger.warning("soffice command not found. Falling back to simple docx extraction without coordinates.")
        except Exception as e:
            logger.warning(f"Unexpected error during soffice conversion: {e}")
            
        # Fallback if LibreOffice is missing or fails
        artifact = ExtractionArtifact(document_id=document_id)
        artifact.warnings.append("DOCX processing without Canonical PDF coordinates. soffice conversion failed or not found.")
        
        try:
            import docx
            doc = docx.Document(file_path)
        except Exception as e:
            artifact.warnings.append(f"Failed to open DOCX: {str(e)}")
            return artifact
            
        dummy_bbox = CoordinateContract(
            page_index=0, x0=0, y0=0, x1=0, y1=0, page_width=0, page_height=0
        )
        
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                if p.style.name.startswith('Heading'):
                    level = 1
                    try:
                        level = int(p.style.name.split(' ')[-1])
                    except ValueError:
                        pass
                    artifact.headings.append(Heading(text=text, level=level, bbox=dummy_bbox))
                else:
                    artifact.spans.append(TextSpan(text=text, bbox=dummy_bbox))
                    
        return artifact


def extract_document(file_path: Path, document_id: UUID, mime_type: str) -> ExtractionArtifact:
    """Factory function to choose the correct extractor based on mime type."""
    if mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
        return PDFExtractor().extract(file_path, document_id)
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file_path.suffix.lower() == ".docx":
        return DOCXExtractor().extract(file_path, document_id)
    else:
        artifact = ExtractionArtifact(document_id=document_id)
        artifact.warnings.append(f"Unsupported file type: {mime_type}")
        return artifact
