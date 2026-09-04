# Document QC & Traceability Audit

Monorepo for a deterministic, non-LLM document quality-control application for
engineering PDF and DOCX deliverables.

## Repository Status

The project is in **M0 — Foundation and Contract Gate**. The existing frontend
and backend are scaffolds, not a completed Sprint 1 implementation. Do not start
later pipeline features until their dependencies and milestone gates pass.

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

## Current Smoke Commands

Frontend:

```powershell
Set-Location frontend
npm ci
npm run lint
npm run build
```

Backend dependencies currently exist, but the reproducible backend quality
commands will be established by M0.4. Do not treat importing the current
`/health` scaffold as completion of the backend foundation.

## Secrets

Never commit `.env` files, uploaded documents, generated audit artifacts, or
Stitch credentials. Stitch MCP configuration and its API key are local user
configuration. Only versioned, non-secret design snapshots belong in `docs/`.
