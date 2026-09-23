# Architecture

Extraction creates canonical page/text/table evidence. Deterministic analyzers emit normalized findings with coordinates. Curation persists `included_in_report` and an optional note. `pypdf` annotates source PDF pages and `python-docx` builds review reports.

## Locale and report rendering

The browser-only locale layer lives in `frontend/src/lib/i18n.ts` and `frontend/src/components/layout/locale-provider.tsx`. It supports `en` and `id`, detects `navigator.language` on first visit, persists explicit choices under `matqc-locale`, and updates the document language attribute after hydration. It does not alter authentication, database models, analyzer output, or persisted findings.

The formal report language crosses the API boundary as `ReportLanguage` (`en` or `id`). `GET /documents/{id}/report?language=...` localizes the preview summary. `GET /documents/{id}/export?format=docx&language=...` selects the DOCX catalog at render time; the PDF branch ignores language and continues to call the original annotation renderer. `backend/services/report_locale.py` owns immutable renderer copy, while `ReportSynthesizer` owns generated localized system prose.

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

## Workspace Identity and Membership

PRISM keeps its own project master data and treats BIMA as the upstream directory. `POST /api/v1/projects/sync-bima` (lead/superuser) fetches BIMA `GET /api/projects` and `GET /api/users`, runs both payloads through `backend/services/bima_adapter.py`, and persists the result in one transaction: referenced users are JIT-provisioned by `upsert_bima_user`, then projects are upserted and matched **solely** on the unique `projects.bima_project_id`. Any contract violation aborts with 502 before a single write, so a malformed upstream payload can never leave a half-synced workspace.

Membership lives in the `project_members` association table (`project_id`, `user_id`, composite primary key, cascading deletes). It is a read-authorization concept: engineers who are project members can see the project and every document inside it, while all write operations keep their existing role- and ownership-based rules. `backend/core/dependencies.py::check_document_read_access` is the single document-level decision point, and async callers must eager-load `Project.members` because membership uses default lazy loading.

Browser traffic never targets a backend host directly. The frontend issues same-origin `/api/v1` requests and `frontend/next.config.ts` rewrites them to `INTERNAL_BACKEND_URL` (default `http://backend:8000`). Server-side renders use the same default, so no API host is compiled into the browser bundle.

## Standards Reference Packs

Future standards packs live outside Git in a licensed reference-library volume with manifests for edition, license, rules, chunks, and source pages. Raw standards PDFs are not ingested by v1.

