# Agent Handoff — 2026-09-04

## Resume point

Resume **M1.2 — secure native-text upload**.  Work is intentionally paused before
the final frontend quality command and before the local commit.  Do not push to
GitHub; the product owner will push manually.

## Repository state

- Current committed HEAD: `84fda56 docs(stitch): record MCP verification state`
- Existing local commits are authored with the repository user's Git identity.
- M1.2 files are uncommitted.  Preserve all of them and do not discard work.
- The product defaults/acceptance matrix are approved in commit `0ad2c09`.
- The project is a root monorepo: `backend/` FastAPI and `frontend/` Next.js.

## M1.2 implementation already completed locally

- Secure `POST /documents/upload` path:
  - accepts only byte-verified PDF/DOCX;
  - normalizes untrusted filenames;
  - limits file size during streaming storage;
  - validates DOCX archive entry count, traversal paths, encryption, expanded
    size, compression ratio, and required DOCX parts;
  - stores atomically via local storage, cleans rejected temporary data;
  - deduplicates simultaneous queued/processing scans by SHA-256;
  - returns `201` for a new scan or `200` plus `deduplicated: true` for reuse.
- Added PostgreSQL partial unique index migration
  `backend/alembic/versions/20260904_0002_active_scan_hash.py`.
- Updated OpenAPI and regenerated
  `frontend/src/lib/api-schema.d.ts` successfully.

## Verification result

Backend verification is complete and passed:

```powershell
Set-Location C:\Werk\DocsQA\backend
.\scripts\quality.ps1
```

Result: Ruff passed, strict mypy passed (34 source files), pytest passed (21
tests), OpenAPI export passed, Alembic offline SQL passed.  The script warns that
`backend/venv` is legacy Python 3.14.7; `.nvmrc`/`.python-version` pin the
intended runtimes.  This warning is non-blocking but must be resolved in M1.3
or environment setup.

The frontend command was started then deliberately terminated at the user's
request to pause, so it must be rerun:

```powershell
Set-Location C:\Werk\DocsQA\frontend
npm run generate:api
npm run check
```

If it passes, first inspect the changes, update
`docs/implementation_readiness_and_execution_plan.md` to mark M1.2 complete
locally, then commit only locally.  Suggested commit message:

```text
feat(upload): add secure native document ingestion
```

Do **not** run `git push`.

## Known limits / next work

- Docker/Postgres/Redis integration is pending local Docker availability; the
  migration is validated as offline SQL but not applied to a live database.
- M1.2 validator tests are unit-level.  Add authenticated endpoint/integration
  coverage once the database runtime is available.
- M1.3 is the next planned milestone after committing M1.2: document status and
  staging state transitions plus worker/queue plumbing.

## Stitch MCP

- Do not request or paste API secrets in the chat or repository.
- `docs/design_system.md` and `docs/design_handoff.md` remain templates waiting
  for a verified Stitch session.
- On the new device, connect/authenticate Stitch in Codex Desktop Settings → MCP
  servers, restart or begin a fresh task, then ask the agent to verify available
  Stitch tools/projects and continue the design handoff.
