# START HERE — DocsQA Execution Index

This is the only document every new agent must read in full. The rest of
`docs/` is a reference corpus: load only the files routed below for the active
ticket. Repository state always overrides stale prose.

## Current checkpoint

- M0, M1, and **M2.1 Revision Sync** are complete locally.
- Next milestone: **M2.2 Standard Traceability**.
- Latest implementation commit: `61ecb4a`.
- Never push to GitHub; the owner pushes. Local commits are allowed.
- The application is a monorepo: `backend/` FastAPI and `frontend/` Next.js.

## Source precedence

1. `Document_QC_WebApp_PRD.md` — product behavior and non-functional rules.
2. `acceptance_matrix.md` — approved limits, states, and release evidence.
3. `backend/openapi.json` — frontend/backend wire contract.
4. `implementation_readiness_and_execution_plan.md` — milestone order/gates.
5. `design_system.md` — versioned Stitch visual tokens only.

If these conflict, record the conflict. Do not silently blend them.

## Minimal reading route

For every continuation:

1. Read this file and `AGENT_HANDOFF_LATEST.md`.
2. Run `git status --short` and `git log --oneline -10`.
3. Read only the active milestone section in
   `implementation_readiness_and_execution_plan.md`.
4. Load the relevant plan: `backend_plan.md` for pipeline/API work or
   `frontend_plan.md` for UI work.
5. Consult the PRD/acceptance matrix only for the feature being implemented.
6. Read every applicable `AGENTS.md` before editing that directory.

Do not make agents reread the whole corpus by default. Historical handoffs and
design notes are evidence, not active instructions.

## Document map

| File | Use when |
|---|---|
| `AGENT_HANDOFF_LATEST.md` | Resuming current work |
| `implementation_readiness_and_execution_plan.md` | Selecting and closing tickets |
| `Document_QC_WebApp_PRD.md` | Resolving product behavior |
| `acceptance_matrix.md` | Limits, lifecycle rules, release tests |
| `backend_plan.md` | Backend architecture or M2/M4/M5 work |
| `frontend_plan.md` | Frontend, review UI, responsive behavior |
| `design_system.md` | Implementing Stitch-derived visuals |
| `design_handoff.md` | Tracing a screen to implementation evidence |
| `development_workflow.md` | Local commands and service setup |
| `agent_execution_playbook.md` | Task-writing and quality conventions |

## Required quality commands

```powershell
Set-Location backend
.\scripts\quality.ps1

Set-Location ..\frontend
npm run generate:api
npm run check
npm run test:e2e
```

Use focused tests during development, then the relevant full gate before a
local commit. Preserve user changes and do not rewrite Git history.

## Stitch and secrets

Stitch project `9978725055094825738` is snapshotted in `design_system.md`.
Stitch is a development-time visual source, not a runtime dependency. Keep API
keys in MCP/secret configuration only—never chat, source, logs, or docs.

## Bootstrap prompt

```text
Read docs/START_HERE.md and docs/AGENT_HANDOFF_LATEST.md in full. Verify Git
state, then work only on the next unblocked milestone using the routed source
documents. Preserve existing changes, run the required quality gate, update
evidence, and commit locally only. Never push to GitHub or store secrets.
```
