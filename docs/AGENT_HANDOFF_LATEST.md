# Agent Handoff — Latest

## Resume point
 
M0, M1, M2 Deterministic Traceability Core, M3 Review and Audit Workflow,
and **M4 Linguistic Pipeline & Governed Engineering Dictionary** are complete locally.
Resume at **M5 Export, Hardening, and Release**.
Read `START_HERE.md` for the compact document routing rules; do not load the
entire docs corpus by default.

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

## Next ticket — M5 Export, Hardening, and Release

Implement the final release milestone (M5.1 - M5.4):

1. **M5.1 Multi-Format Export Service**:
   - Annotated PDF export embedding visual callouts and issue highlight boxes onto document pages;
   - Machine-readable structured export in CSV, XLSX, and JSON formats for audit compliance.
2. **M5.2 Real-time Scan Progress (WebSocket / SSE)**:
   - Server-sent events or WebSocket channel for live pipeline stage progression updates to the frontend workspace.
3. **M5.3 Hardening, Security, Retention & Performance Verification**:
   - Automated retention cleanup policies for ephemeral uploads;
   - Rate limiting, security headers, and large document (200+ pages) benchmark verification.
4. **M5.4 End-to-End Release Runbook & Verification**:
   - Full end-to-end integration tests covering upload -> OCR/extraction -> traceability -> linguistic -> review -> export lifecycle;
   - Docker Compose production stack validation.

## Operational notes

- Intended runtimes: Node.js `24.20.0`, Python `3.13.15`.
- Backend may warn when using legacy `backend/venv` on Python 3.14.7.
- Stitch project: `9978725055094825738`; credentials never belong in the repo.
- Frontend API base defaults to `http://localhost:8000/api/v1` and can be
  overridden with local-only `NEXT_PUBLIC_API_BASE_URL`.
- To test containers: ensure Docker Desktop is running and `docker version`
  works, then run `Copy-Item .env.docker.example .env` followed by
  `docker compose up --build` from the repository root.
