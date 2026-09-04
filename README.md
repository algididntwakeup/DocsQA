# Document QC & Traceability Audit

Monorepo for a deterministic, non-LLM document quality-control application for
engineering PDF and DOCX deliverables.

## Repository Status

The project is complete locally through **M1 — Upload-to-Extraction Vertical
Slice**. The next milestone is M2.1 Revision Sync.

Start every new task or machine setup with
[`docs/START_HERE.md`](docs/START_HERE.md), then use
[`docs/implementation_readiness_and_execution_plan.md`](docs/implementation_readiness_and_execution_plan.md)
as the ordered delivery queue.

## Structure

```text
backend/   FastAPI API and document-processing services
frontend/  Next.js App Router application
docs/      PRD, architecture plans, gates, and agent handoff
```

## Pinned Runtimes

- Node.js `24.20.0` (LTS), recorded in `.nvmrc`
- Python `3.13.15`, recorded in `.python-version`

Use a backend virtual environment named `backend/.venv`. Existing local
environments such as `backend/venv` are ignored and must not be copied between
machines.

## Quality Commands

Frontend:

```powershell
Set-Location frontend
npm ci
npm run lint
npm run build
```

The reproducible backend quality gate can be run from `backend/` with:

```powershell
.\scripts\quality.ps1
```

The frontend equivalent is `npm run check`; its browser happy path is
`npm run test:e2e`.

## Docker Compose

The Compose stack builds and runs PostgreSQL, Redis, database migrations,
FastAPI, the Celery extraction worker, and the production Next.js frontend.

```powershell
Copy-Item .env.docker.example .env
docker compose up --build
```

Open `http://localhost:3000` for the application and
`http://localhost:8000/docs` for the API schema.

```powershell
docker compose ps
docker compose logs -f api worker frontend
docker compose down
```

The normal `down` command preserves named volumes. Add `--volumes` only when
you explicitly intend to delete the local database, queue, and uploaded files.

## Secrets

Never commit `.env` files, uploaded documents, generated audit artifacts, or
Stitch credentials. Stitch MCP configuration and its API key are local user
configuration. Only versioned, non-secret design snapshots belong in `docs/`.
