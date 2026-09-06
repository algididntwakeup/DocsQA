# Agent Handoff — Latest

## Resume point
 
All core and production release milestones (M0, M1, M2 Deterministic Traceability Core,
M3 Review & Audit Workflow, M4 Linguistic Pipeline & Governed Dictionary, and
**M5 Export, Hardening, and Release**) are complete locally.
Read `START_HERE.md` and `release_runbook.md` for operational deployment procedures.

## Verified repository state

- M1.1–M1.4: persistence, secure upload, extraction, Celery orchestration, and
  lifecycle APIs complete locally.
- M1.5 implementation commit: `16fd31f feat(frontend): complete document lifecycle UI`.
- Frontend includes typed fetch client, responsive Stitch-token shell,
  dashboard/list states, 20-file upload queue, per-file results, API errors,
  detail/status polling with capped backoff, and per-stage progress.
- Verification: ESLint, strict TypeScript, 4 Vitest component tests, Next.js
  production build, and Playwright upload-to-extracted happy path all pass.
- Docker Compose provides PostgreSQL and Redis; `backend/.env` is local-only.
- Full application Compose stack (PostgreSQL, Redis, migrate, API, worker,
  frontend): `c8ff84b`. Frontend standalone artifact was smoke-tested at HTTP
  200, but Docker CLI was not visible to the Codex shell, so image build/runtime
  verification remains for a terminal where `docker` is in `PATH`.
- M2.1 implementation: `61ecb4a`. It compares explicit revision values from
  filename, cover page, and the latest revision-table row, persists a versioned
  artifact, and keeps analyzer failures isolated from successful extraction.
- M2.2 implementation: `2152197`. It extracts bounded ASME/API/ASTM/ISO
  citations, separates body and reference entries, matches normalized codes and
  edition years, records location evidence, and isolates the stage in the
  worker. Unknown bare API numbers are surfaced as ambiguous instead of false
  missing-reference findings.
- M2.3 implementation: `20aefc1`. It parses locale-aware `Decimal` numbers, currency and
  engineering units, identifies row/column totals, scopes subtotals and grand
  totals without double counting, evaluates dual-threshold tolerance
  (percentage and unit), surfaces operands/stated/computed/delta/tolerance/location
  evidence, and isolates stage execution in the worker. Forty-nine unit and
  property tests cover parser accuracy, boundaries, units, and malformed rows.
- M2.4 implementation: `311e047`. Extracts structured entries from Table of Contents,
  List of Figures, and List of Tables; resolves roman numeral preliminary
  matter (`i`, `ii`, `iv`) and arabic body page numbers; discovers actual
  targets from headings and captions; computes signed `page_delta`; surfaces
  dual bounding boxes (entry location on ToC page and target location on body page);
  detects missing targets and duplicate captions; and isolates stage execution in
  the worker with `COMPLETED_WITH_WARNINGS` degradation. Thirty-one unit tests
  and pipeline isolation/degradation tests pass.
- M2.5 implementation: unifies findings across Revision Sync, Standard Traceability,
  Table Math, Reference Drift, and Stage Failure diagnostics into canonical
  `Issue` models. Normalizes bounding box coordinates, applies deterministic
  severity mappings and rule IDs (`REVISION_MISMATCH`, `STANDARD_NOT_IN_BIBLIOGRAPHY`,
  `EDITION_YEAR_MISMATCH`, `AMBIGUOUS_STANDARD`, `TABLE_MATH_MISMATCH`, `TOTAL_NOT_FOUND`,
  `UNIT_MISMATCH`, `MALFORMED_TABLE_ROW`, `REF_DRIFT`, `MISSING_TARGET`,
  `DUPLICATE_CAPTION`, `STAGE_FAILURE`), deduplicates identical findings, and persists
  records into PostgreSQL (`issues` table with Alembic migration `20260905_0003_create_issues_table.py`)
  and storage artifact (`artifacts/{document_id}/aggregation.json`). Implemented
  `GET /api/v1/documents/{document_id}/issues` with category filtering, pagination,
  and severity metric tallies. Ten unit tests, 3 API contract tests, and pipeline
  stage tests pass.
- M3 implementation: complete review and audit workflow across backend and frontend:
  - Canonical PDF streaming: `GET /api/v1/documents/{document_id}/pdf` delivers inline PDF stream with validation.
  - Optimistically locked issue decisions: `PATCH /api/v1/issues/{issue_id}/decision` supports `ACCEPTED`, `REJECTED`, `FLAGGED`, `EDITED` with version checking (HTTP 409 on concurrent collision).
  - Lead Reviewer dispositions: `PATCH /api/v1/issues/{issue_id}/disposition` enforces mandatory non-empty justification (HTTP 422 if omitted), records reviewer identity, and increments version.
  - Prohibition of traceability bulk acceptance: `POST /api/v1/issues/bulk-decision` strictly enforces PRD §3.2 & Scenario A-10 by rejecting any traceability finding with HTTP 422; frontend UI features prominent PRD §3.2 banner and disables bulk action for traceability.
  - Append-only audit trail: `AuditEvent` model, migration `20260905_0004_create_audit_events_and_issue_tracking.py`, `GET /api/v1/documents/{document_id}/audit-events`, and `POST /api/v1/documents/{document_id}/disposition`.
  - Traceability audit summary: `GET /api/v1/documents/{document_id}/traceability-summary`.
  - Frontend split-screen review workspace: `/documents/[id]/review` page route, `SplitScreenViewer`, `DocumentViewer` with page navigation and zoom, `HighlightOverlay` with single/dual/operand bounding boxes, `IssueCard` with typed evidence views and OCC conflict handling, `IssuePanel` with Traceability/Language tabs, `AuditTrailModal`, and `TraceabilitySummaryModal`.
  - Quality verification: Backend passes Ruff, strict mypy across 53 files, and 158 tests in `quality.ps1`. Frontend passes ESLint, `tsc --noEmit`, 18 Vitest tests across 6 suites, and `next build` in `npm run check`.
- All commits stay local. Do not run `git push`.

- M4 implementation: complete linguistic analysis pipeline and governed custom dictionary:
  - M4.2 Governed Custom Engineering Dictionary: `DictionaryTerm` model with composite index `(scope, term)`, Alembic migration `20260906_0005_create_dictionary_terms.py`, REST endpoints `POST /api/v1/dictionary/terms`, `GET /api/v1/dictionary/terms`, `PATCH /api/v1/dictionary/terms/{id}/approve` supporting `PENDING`, `APPROVED`, `REJECTED` workflows.
  - M4.1a Deterministic Typo & Spelling Detection: `pyspellchecker` integration cross-referenced against approved custom dictionary terms, 100+ standard engineering/metallurgical acronyms (ASME, ASTM, NACE, etc.), chemical elements, and material specifications to guarantee false positives < 5%.
  - M4.1b Grammar & Style Analysis: LanguageTool integration with circuit-breaker pattern, fallback degradation, suppression of technical writing false positives (imperative instructions, sentence fragments in tables/headings), and deterministic offline rules for repeated words, common homophones, and subject-verb agreement.
  - M4.3 Near-Duplicate Content Detection: `thefuzz` token sort ratio >= 85% with dual-location bounding box evidence (original occurrence and duplicate occurrence), header/footer suppression, and minimum length threshold.
  - M4.4 Contextual Ambiguity & Passive Voice: Inconsistent material grades (e.g. 316 vs 316L, 304 vs 304L), vague directive phrases ("as appropriate", "sufficient", "workmanlike"), and passive voice detection with deterministic active voice rewrite suggestions.
  - Pipeline & Aggregation: Unified linguistic finding aggregation into `IssueRead` records (`category=IssueCategory.LINGUISTIC`, `evidence.kind="LINGUISTIC"`), Celery pipeline stages (`spellcheck`, `grammar`, `duplicate`, `ambiguity`) with isolated failure handling and `COMPLETED_WITH_WARNINGS` degradation.
  - Frontend: `DictionaryModal` for term management, approval workflows, and status filtering; "Add to Dictionary" CTA button on spelling issue cards pre-filling the submission form; safe location coordinate handling; Language tab bulk acceptance allowed per PRD §3.2.
  - Quality verification: Backend passes Ruff, strict mypy across 60 files, and 186 tests in `quality.ps1`. Frontend passes ESLint, `tsc --noEmit`, 23 Vitest tests across 7 suites, and `next build` in `npm run check`.
- All commits stay local. Do not run `git push`.

- M5 implementation: complete export services, scan telemetry SSE, and release hardening:
  - M5.1 Multi-Format Export Service (`backend/services/export.py`):
    - Annotated PDF (`export_annotated_pdf`): injects coordinate-accurate bounding boxes and callouts onto the original PDF using pure-Python `pypdf`.
    - Multi-sheet Excel workbook (`export_excel_workbook`): formatted tabs for Executive Summary, Traceability Findings, Linguistic Findings, and full Audit Trail with auto-adjusted column dimensions.
    - Flat CSV (`export_csv_issues`): RFC 4180 compliant issue log with findings, locations, decisions, and lead dispositions.
    - JSON audit package (`export_json_audit_bundle`): complete cryptographic audit bundle with document SHA-256 hash, raw analyzer evidence, and event ledger.
    - REST export endpoint: `GET /api/v1/documents/{document_id}/export?format=pdf|xlsx|csv|json`.
  - M5.2 Real-time Scan Progress via Server-Sent Events (`backend/api/documents.py`):
    - `GET /api/v1/documents/{document_id}/events`: streaming progress events with terminal detection and graceful close.
    - Frontend integration (`frontend/src/components/document/document-status-view.tsx`): live event stream updates with automatic fallback to polling if SSE is unsupported or fails.
  - M5.3 Security Hardening, Ephemeral Retention & Middleware:
    - HTTP security headers middleware in `backend/main.py`: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`.
    - Retention service (`backend/services/retention.py`): purges expired documents, disk storage files, and extraction artifacts exceeding the 30-day retention boundary per PRD §4.3.
  - M5.4 Frontend Export UI & Verification (`frontend/src/components/review/export-modal.tsx`):
    - "Export" button in split-screen review workspace header opening the multi-format export modal.
    - 4 distinct download cards with direct download URLs and format badges.
  - Verification & Release Runbook:
    - Comprehensive end-to-end integration test (`backend/tests/test_e2e_lifecycle.py`): tests ingestion -> analyzers -> OCC issue decisions -> Lead Reviewer disposition -> all 4 exports.
    - `backend/scripts/quality.ps1` 100% green: 195 passed tests, 0 Ruff errors, 0 strict Mypy errors across 64 files, valid OpenAPI export, and offline Alembic check.
    - `frontend/npm run check` 100% green: 0 ESLint errors, 0 TypeScript errors, 28 passed Vitest tests across 8 suites, and clean Next.js 16 production build.
    - Production operations guide published at `docs/release_runbook.md`.
- Document Deletion & UI Features:
  - Backend `DELETE /api/v1/documents/{document_id}`: deletes database record (cascading to stage_runs, issues, audit_events), storage files, and disk artifacts directory (`artifacts/{document_id}`).
  - Frontend DocumentList: added Actions column with delete button and confirmation dialog.
  - Frontend DocumentStatusView: added delete button with confirmation dialog.
  - Frontend Light Mode: added `ThemeToggle` component in `AppShell` and `SplitScreenViewer` with full light theme tokens in `globals.css` and `localStorage` persistence (`matqc-theme`).
- Extraction Pipeline Bug Fixes (commits `3fcc885`, `0b060b3`):
  - **Bug 1 — SSE not real-time** (`3fcc885`): `event_generator()` in `api/documents.py` was one-shot. Fixed to poll DB every 2 s in an `asyncio` loop until terminal status.
  - **Bug 2 — Celery no timeout** (`3fcc885`): `extract_document_task` had no `soft_time_limit`/`time_limit` and used `autoretry_for=(Exception,)`. Fixed: added `soft_time_limit=180`, `time_limit=240`, removed autoretry, added `SoftTimeLimitExceeded` handler → `COMPLETED_WITH_WARNINGS`.
  - **Bug 3 — CAD table explosion** (`3fcc885`): `find_tables()` on CAD PDFs produced 30 000+ phantom cells. Fixed: 20 s per-page timeout, cap 20 tables/page, skip tables > 500 cells/100 rows/30 cols.
  - **Bug 4 — `float` not subscriptable** (`0b060b3`): `Table.cells` is a *flat* `list[tuple]`, not a 2D grid. Iterating it as rows×cols made `cell_rect` a float. Fixed: use `table.rows` → `TableRow.cells` for proper 2D iteration. `finder.tables` replaces `list(TableFinder)`.
  - Full incident post-mortem + PyMuPDF API reference in `docs/troubleshooting_pipeline_stuck.md`.
- All commits stay local. Do not run `git push`.

## Operational notes

- Intended runtimes: Node.js `24.20.0`, Python `3.13.15`.
- Backend may warn when using legacy `backend/venv` on Python 3.14.7.
- Stitch project: `9978725055094825738`; credentials never belong in the repo.
- Frontend API base defaults to `http://localhost:8000/api/v1` and can be
  overridden with local-only `NEXT_PUBLIC_API_BASE_URL`.
- To test containers: ensure Docker Desktop is running and `docker version`
  works, then run `Copy-Item .env.docker.example .env` followed by
  `docker compose up --build` from the repository root.
- Extraction pipeline bugs are all fixed. `docs/troubleshooting_pipeline_stuck.md`
  is an incident post-mortem with a PyMuPDF API reference — read it before
  touching `backend/services/extract.py`.
- Backend quality gate: 197 passed, 2 skipped (PyMuPDF DLL + Redis integration).
