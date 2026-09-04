# Agent Handoff — Latest

## Resume point

M1 and **M2.1 Revision Sync** are complete locally. Resume at **M2.2 Standard
Traceability**. Read `START_HERE.md` for the compact document routing rules; do
not load the entire docs corpus by default.

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
- Backend gate: Ruff and strict mypy pass; 39 tests pass, with the PyMuPDF DLL
  and live Redis/Postgres integration checks skipped in the current host.
- All commits stay local. Do not run `git push`.

## Next ticket — M2.2 Standard Traceability

Implement deterministic extraction and matching of standards/codes between
document body citations and the bibliography/reference section:

1. define bounded registry patterns and normalized code/edition tokens;
2. identify body vs reference-section boundaries from extraction artifacts;
3. emit present, missing bibliography, edition mismatch, and ambiguous evidence;
4. integrate it as an independent versioned worker stage.

Require match/missing/year-mismatch/ambiguous/malformed fixtures, false-positive
assertions, and pipeline/API integration evidence. Do not start table math,
reference drift, aggregation, review UI, or linguistic work in the same ticket.

## Operational notes

- Intended runtimes: Node.js `24.20.0`, Python `3.13.15`.
- Backend may warn when using legacy `backend/venv` on Python 3.14.7.
- Stitch project: `9978725055094825738`; credentials never belong in the repo.
- Frontend API base defaults to `http://localhost:8000/api/v1` and can be
  overridden with local-only `NEXT_PUBLIC_API_BASE_URL`.
- To test containers: ensure Docker Desktop is running and `docker version`
  works, then run `Copy-Item .env.docker.example .env` followed by
  `docker compose up --build` from the repository root.
