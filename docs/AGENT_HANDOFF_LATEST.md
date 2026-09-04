# Agent Handoff — Latest

## Resume point

M1 is complete locally through **M1.5 Minimal Frontend Lifecycle**. Resume at
**M2.1 Revision Sync**. Read `START_HERE.md` for the compact document routing
rules; do not load the entire docs corpus by default.

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
- All commits stay local. Do not run `git push`.

## Next ticket — M2.1 Revision Sync

Implement deterministic comparison of revision tokens extracted from:

1. source filename;
2. document cover;
3. revision-history table.

Normalize tokens before comparison and emit evidence-rich mismatch/missing
source results. Required tests: correct match, each pairwise mismatch,
three-way mismatch, missing/malformed sources, false-positive assertions, and
an API/pipeline integration test. A revision analyzer failure must not discard
successful extraction or prevent later independent analyzers.

Before editing, inspect current extraction artifacts/models and define the
smallest versioned analyzer interface compatible with M2.5 aggregation. Do not
start standards, table-math, reference-drift, review UI, or linguistic work in
the same ticket.

## Operational notes

- Intended runtimes: Node.js `24.20.0`, Python `3.13.15`.
- Backend may warn when using legacy `backend/venv` on Python 3.14.7.
- Stitch project: `9978725055094825738`; credentials never belong in the repo.
- Frontend API base defaults to `http://localhost:8000/api/v1` and can be
  overridden with local-only `NEXT_PUBLIC_API_BASE_URL`.
