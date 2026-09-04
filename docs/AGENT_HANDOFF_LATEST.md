# Agent Handoff (Latest)

## Resume point

Resume **DocsQA Project** starting from **M1.5 (Minimal frontend lifecycle)**.
All commits should be made **locally only**. Do not push to GitHub; the product
owner will push manually.

## Repository state

- M1.2 (Secure native-text upload) is **COMPLETE**.
- M0.5 (Stitch MCP Setup & Baseline) is **COMPLETE**. `docs/design_system.md` has
  been generated from Stitch Project `9978725055094825738`.
- M1.3 (Versioned extraction service) is **COMPLETE**. PDFExtractor (PyMuPDF) and
  DOCXExtractor (soffice fallback), schemas, and unit tests. The extract module
  was later repaired to pass ruff + strict mypy.
- M1.4 (Celery orchestration and status API) is **COMPLETE locally**. `docqc.extract`
  task, `services/pipeline.py` enqueue-after-commit, and implemented
  `GET /api/v1/documents`, `/{id}`, `/{id}/status`. A Redis-backed integration
  smoke test (`RUN_REDIS_INTEGRATION=1`, opt-in) passes against live
  Postgres/Redis.
- Latest local commit: `feat(pipeline): add Celery extraction orchestration and status API (M1.4)`.
- Existing local commits are authored with the repository user's Git identity.
- The project is a root monorepo: `backend/` FastAPI and `frontend/` Next.js.
- Local infra runs via `docker compose up -d` (Postgres 17, Redis 7.4). A local
  `backend/.env` was created from `.env.example` and the DB migrated to `head`.

## Next Work (M1.5)

- Review `docs/implementation_readiness_and_execution_plan.md` to confirm the
  M1.5 ticket and dependencies (M0.3, M0.5, M1.2, M1.4 are all complete).
- **M1.5 Minimal frontend lifecycle**: Initialize the Next.js structure using the
  Stitch design tokens in `docs/design_system.md`, wire the generated API client
  (`frontend/src/lib/api-schema.d.ts`), and implement accessible upload, error
  states, polling with backoff, document list, and per-stage progress. No
  split-screen or mock issue data yet.

## General Rules

- Do **not** run `git push`. All commits remain local.
- For Stitch / MCP usage on a new device, ensure the Stitch MCP server is
  authenticated via Settings -> MCP Servers.
- Use `npm run generate:api` and `npm run check` in `frontend` for frontend
  validation.
- Use `pytest tests/ -v` and `scripts/quality.ps1` in `backend` for backend
  validation. (Note: PyMuPDF DLLs may skip tests locally if the Windows container
  lacks specific VC++ dependencies, but logic should remain structurally
  complete. The Redis integration test is opt-in via `RUN_REDIS_INTEGRATION=1`.)
