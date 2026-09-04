# Agent Handoff — Latest

## Resume point

M1, **M2.1 Revision Sync**, and **M2.2 Standard Traceability** are complete
locally. Resume at **M2.3 Table Math**. Read `START_HERE.md` for the compact
document routing rules; do not load the entire docs corpus by default.

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
- Backend gate: Ruff and strict mypy pass; 48 tests pass, with the PyMuPDF DLL
  and live Redis/Postgres integration checks skipped in the current host.
- All commits stay local. Do not run `git push`.

## Next ticket — M2.3 Table Math

Implement deterministic validation of flat-table totals:

1. parse locale-aware decimal values and explicit units without float math;
2. identify row/column totals and subtotal scope in extracted flat tables;
3. apply the approved absolute/percentage tolerance policy;
4. emit operands, stated value, computed value, delta, tolerance, and locations;
5. integrate it as an independent versioned worker stage.

Require correct/mismatch/rounding-boundary/unit/thousands/decimal-separator and
malformed-row fixtures, property-style parser tests, false-positive assertions,
and pipeline/API integration evidence. Do not start reference drift,
aggregation, review UI, or linguistic work in the same ticket.

## Operational notes

- Intended runtimes: Node.js `24.20.0`, Python `3.13.15`.
- Backend may warn when using legacy `backend/venv` on Python 3.14.7.
- Stitch project: `9978725055094825738`; credentials never belong in the repo.
- Frontend API base defaults to `http://localhost:8000/api/v1` and can be
  overridden with local-only `NEXT_PUBLIC_API_BASE_URL`.
- To test containers: ensure Docker Desktop is running and `docker version`
  works, then run `Copy-Item .env.docker.example .env` followed by
  `docker compose up --build` from the repository root.
