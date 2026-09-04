# Agent Execution Playbook — Document QC System

> **Purpose:** Step-by-step guide for any AI coding agent (or developer) to pick up and execute development tasks on this project in a structured, predictable manner.

> **Current delivery status (2026-09-04):** The repository is still a scaffold
> and has not passed the Foundation gate. Use
> `docs/implementation_readiness_and_execution_plan.md` as the ordered execution
> queue. The sprint list below describes intended scope, not completed work.

---

## 1. Pre-Flight Checklist

Before starting any development work, confirm:

- [ ] You have read `docs/START_HERE.md` when joining from a new task or machine
- [ ] You have read `docs/Document_QC_WebApp_PRD.md` (the source of truth for all requirements)
- [ ] You understand the target architecture (§4 of the PRD)
- [ ] You know which sprint/phase the task belongs to (see `docs/development_workflow.md`)
- [ ] The relevant plan document has been reviewed (`docs/backend_plan.md` or `docs/frontend_plan.md`)
- [ ] The ticket is the next unblocked item in `docs/implementation_readiness_and_execution_plan.md`
- [ ] Its dependencies, tests, definition of done, and non-goals are explicit
- [ ] For frontend work, the Stitch MCP source screen and versioned design
      snapshot are identified; no Stitch credential is written to the repo

---

## 2. Task Execution Protocol

### 2.1 Understand → Plan → Implement → Verify

Every task follows this loop:

```
1. UNDERSTAND  — Read the PRD section + relevant plan document for the feature
2. PLAN        — Identify affected files, dependencies, and edge cases
3. IMPLEMENT   — Write code following the modular service architecture
4. VERIFY      — Run tests, type-checks, linters; manually test if UI-related
5. DOCUMENT    — Update inline TODOs, docstrings, and this playbook if needed
```

### 2.2 File Ownership Rules

| Layer | Owner Directory | Naming Convention |
|---|---|---|
| API Routes | `backend/api/` | `{resource}.py` (e.g., `documents.py`) |
| Business Logic | `backend/services/` | `{pipeline_stage}.py` (e.g., `trace_numbers.py`) |
| Configuration | `backend/core/` | `config.py` |
| Frontend Pages | `frontend/src/app/` | Next.js App Router conventions |
| Frontend Components | `frontend/src/components/` | PascalCase (e.g., `SplitScreenViewer.tsx`) |

### 2.3 Dependency Rules

- **Services are independent.** Each service in `backend/services/` must be self-contained. A failure in `trace_numbers.py` must NOT crash `spellcheck.py`.
- **Services share `extract.py` output.** All pipeline stages receive the extraction result as input — they do not call `extract.py` themselves.
- **API layer is thin.** `backend/api/` routers call services; they do NOT contain business logic.
- **Frontend calls backend only via `/api/v1/*`.** No direct DB access from frontend.

---

## 3. Implementation Order (Recommended)

### M0 — Foundation and Contract Gate (must run first)
1. Normalize repository/runtime boundaries
2. Freeze MVP decisions and acceptance matrix
3. Define backend domain models + OpenAPI contract
4. Add executable lint/type/test/build gates
5. Connect Stitch MCP and create a versioned design handoff snapshot

### M1 — Upload-to-Extraction Vertical Slice
1. Infrastructure, persistence, and storage adapter
2. Secure upload endpoint
3. Versioned PDF/DOCX extraction with canonical PDF rendition
4. Celery orchestration + status endpoint
5. Upload UI + basic document list/status page

### M2 — Deterministic Traceability Core (P0-CRITICAL)
1. `backend/services/revision_sync.py` — Revision sync
2. `backend/services/standard_traceability.py` — Standard traceability
3. `backend/services/trace_numbers.py` — Table math validation
4. `backend/services/ref_drift.py` — Reference drift detection
5. `backend/services/aggregate.py` — Versioned issue aggregation

### M3 — Review and Audit Workflow
1. `frontend` — Split-screen canonical PDF viewer + issue panel
2. Review decisions, dispositions, optimistic locking, and audit events
3. Authentication/RBAC before shared deployment

### M4 — Linguistic Pipeline
1. `backend/services/spellcheck.py` — Spelling detection
2. `backend/services/duplicate.py` — Duplicate detection
3. `backend/services/grammar.py` — Grammar via LanguageTool
4. `backend/services/ambiguity.py` — Contextual ambiguity
5. Custom Dictionary CRUD + governance UI

### M5 — Export, Hardening, and Release
1. Export endpoints (annotated PDF, CSV/XLSX)
2. WebSocket/SSE for real-time scan progress
3. Retention, security, backup/restore, and performance checks
4. End-to-end testing and release runbook

---

## 4. Code Quality Gates

Before marking any task as complete:

- [ ] No `type: ignore` without a comment explaining why
- [ ] All new functions have docstrings
- [ ] API endpoints have Pydantic request/response models
- [ ] Services return typed dataclasses/Pydantic models, not raw dicts
- [ ] Frontend components have TypeScript interfaces for props
- [ ] No hardcoded values — use `core/config.py` or environment variables

---

## 5. Error Handling Convention

```python
# Backend services: always catch and return structured errors
class ServiceResult:
    success: bool
    data: Any | None
    error: str | None
    stage: str  # e.g., "trace_numbers"
```

- Pipeline stages MUST NOT raise unhandled exceptions
- Use `STAGE_FAILED` informational issue for partial failures
- API layer translates `ServiceResult` to HTTP responses

---

## 6. Testing Strategy

| Layer | Tool | Minimum Coverage |
|---|---|---|
| Services (unit) | pytest | Each service has ≥1 happy-path + ≥1 error-path test |
| API (integration) | pytest + httpx | Each endpoint has request/response validation tests |
| Frontend (component) | Jest + React Testing Library | Critical UI components (SplitScreen, IssuePanel) |
| E2E | Playwright | Upload → Scan → Review → Export flow |

---

## 7. Commit Message Convention

```
<type>(<scope>): <description>

feat(services/trace_numbers): implement table sum recomputation
fix(api/documents): handle empty file upload gracefully
docs(playbook): add sprint 3 implementation notes
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
