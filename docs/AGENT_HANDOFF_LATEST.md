# Agent Handoff — Latest

## Resume point
 
M0, M1, and **M2 Deterministic Traceability Core** (M2.1 Revision Sync,
M2.2 Standard Traceability, M2.3 Table Math, M2.4 Reference Drift, and
M2.5 Issue Aggregation & Persistence) are complete locally. Resume at **M3 Review and Audit Workflow**.
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
- Backend gate: Ruff and strict mypy pass across 50 files; 147 tests pass, with the
  PyMuPDF DLL and live Redis/Postgres integration checks skipped in the current host.
- All commits stay local. Do not run `git push`.

## Next ticket — M3 Review and Audit Workflow

Implement the reviewer interface and audit trail (M3.1 - M3.5):

1. **M3.1 PDF Viewer & Review Shell**:
   - Read-only canonical PDF viewer with PDF.js and stable page navigation;
   - Responsive split layout (document view + issues panel) adhering to Stitch tokens;
2. **M3.2 Issue Panel & Navigation**:
   - Traceability/Language issue tabs, severity/category filters, virtualization;
   - Single- and dual-location highlight overlays using canonical bounding box coordinates;
   - Deep linking directly to issues and page coordinates;
3. **M3.3 Issue Decision & Optimistic Locking**:
   - Accept/Reject/False Positive decisions with user attribution and reason comments;
   - Optimistic concurrency control via `version` field;
4. **M3.4 Lead Reviewer Disposition & Audit Log**:
   - Disposition lifecycle (Approved / Changes Requested) with permission enforcement;
   - Immutable append-only audit event stream for all decisions and dispositions.

## Operational notes

- Intended runtimes: Node.js `24.20.0`, Python `3.13.15`.
- Backend may warn when using legacy `backend/venv` on Python 3.14.7.
- Stitch project: `9978725055094825738`; credentials never belong in the repo.
- Frontend API base defaults to `http://localhost:8000/api/v1` and can be
  overridden with local-only `NEXT_PUBLIC_API_BASE_URL`.
- To test containers: ensure Docker Desktop is running and `docker version`
  works, then run `Copy-Item .env.docker.example .env` followed by
  `docker compose up --build` from the repository root.
