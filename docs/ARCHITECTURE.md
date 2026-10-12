# Architecture

Extraction creates canonical page/text/table evidence. Deterministic analyzers emit normalized findings with coordinates. Curation persists `included_in_report` and an optional note. `pypdf` annotates source PDF pages and `python-docx` builds review reports.

## Locale and report rendering

The browser-only locale layer lives in `frontend/src/lib/i18n.ts` and `frontend/src/components/layout/locale-provider.tsx`. It supports `en` and `id`, detects `navigator.language` on first visit, persists explicit choices under `matqc-locale`, and updates the document language attribute after hydration. It does not alter authentication, database models, analyzer output, or persisted findings.

The formal report language crosses the API boundary as `ReportLanguage` (`en` or `id`). `GET /documents/{id}/report?language=...` localizes the preview summary. `GET /documents/{id}/export?format=docx|pdf&language=...` selects the DOCX catalog at render time; PDF review reports are converted from the generated DOCX by Headless LibreOffice. The separate `annotated_pdf` format continues to annotate the original source. `backend/services/report_locale.py` owns immutable renderer copy, while `ReportSynthesizer` owns generated localized system prose. Language and mechanics findings are excluded from report exports by default; `include_language_mechanics=true` opts in. Repeated findings with the same type, source phrase, and suggestion are grouped across their affected pages.

Project report branding is stored in `projects.header_config` and validated by `schemas.report.HeaderTemplateConfig`. `PUT /projects/{id}/header-config` saves project defaults; export-dialog changes are sent as a `header_config` override in a POST to the document export route and are not persisted. `services.docx_styler.apply_document_header()` builds the repeating three-column header used by both DOCX and converted PDF exports. The browser preview and project settings share `HeaderTemplateConfigEditor`.

Only renderer-owned labels and prose are translated. Persisted analyzer/reviewer/document content—including evidence, finding messages and codes, technical identifiers, source excerpts, and reviewer notes—is copied verbatim to preserve audit traceability. No translation dependency or machine-translation service is used.

## Layout, Typography & Page-Continuity Diagnostics

The extraction pipeline includes `DocumentLayoutInspector` (`backend/services/layout_inspector.py`) that uses PyMuPDF (`fitz`) coordinates and font dictionaries to detect document integrity and layout defects:

1. **Cross-Page Sentence Breaks** (`detect_cross_page_sentence_breaks`):
   - Flags sentences severed across page boundaries where page $N$ ends with conjunctions (`and`, `or`), continuation punctuation (commas, dashes), or lacks terminal punctuation, and text continues on page $N+1$ (e.g., `"Table 6-3 and"`).
2. **Style & Typography Misclassification** (`detect_style_misclassification`):
   - Flags narrative or descriptive body sentences (`Based on...`, `Referring to...`, `According to...`) formatted with bold typography, heading flags, or outline bookmarks.
3. **Unintended Whitespace / Void Pages** (`detect_unintended_whitespace`):
   - Flags middle pages ($0 < \text{page\_index} < N-1$) with text utilization ratio $< 25\%$ (largely blank or void pages before section transitions), while exempting cover and back pages.
4. **Uncontrolled Pages Audit** (`audit_uncontrolled_pages`):
   - Verifies that every page (portrait and landscape) contains all 4 required control elements: running header, running footer, page number, and document number.
5. **Front Matter Navigation Drift** (`validate_front_matter_navigation`):
   - Computes drift between page numbers listed in Table of Contents / Figures / Tables and the physical page locations of target items.

Normalized data structures in `backend/schemas/extraction.py`:
- `PageBlock`: Text/media blocks with coordinates, font metadata (`font_name`, `font_size`, `is_bold`, `is_italic`), and classification (`is_heading`, `is_outline`).
- `PageMetric`: Page-level density and `text_utilization_ratio`.
- `PDFPage`: Page geometry, orientation (`portrait` vs `landscape`), and control elements.
- `LayoutAnomaly`: Normalized diagnostic findings.

## Workspace Identity and Import

PRISM keeps its own project master data and treats BIMA as a read-only, flat upstream catalog. `GET /api/v1/bima/catalog` proxies BIMA `GET /api/projects` and annotates each row with local import state (`is_imported`, `prism_project_id`) from one lookup on `projects.bima_project_id`. Projects enter PRISM on demand through `POST /api/v1/projects/import-bima`, which is idempotent on `bima_project_id` (existing row → 200, new row → 201), sets `projects.owner_id` to the calling user, and provisions the workspace directory. There is no directory sync, no membership table, and no per-project BIMA detail fetch.

Project read access is ownership- or document-based: `backend/core/dependencies.py::check_document_read_access` grants access to the document PIC, the uploader, the owner of the parent project, and lead engineers/superusers. All write operations keep their existing role- and ownership-based rules.

Spellcheck suppresses equipment tags, alphanumeric identifiers, standard engineering and Indonesian company terms, and all terms registered in the applicable organization/project dictionary scopes. Repeated language findings are grouped in exported review reports by finding type, source phrase, and suggestion so recurring benign terms do not create one row per page.

Browser traffic never targets a backend host directly. The frontend issues same-origin `/api/v1` requests and `frontend/next.config.ts` rewrites them to `INTERNAL_BACKEND_URL` (default `http://backend:8000`). Server-side renders use the same default, so no API host is compiled into the browser bundle.

## Standards Reference Packs

Future standards packs live outside Git in a licensed reference-library volume with manifests for edition, license, rules, chunks, and source pages. Raw standards PDFs are not ingested by v1.

