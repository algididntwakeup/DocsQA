# Implementation Readiness & Agent Execution Plan

**Audit date:** 2026-09-04  
**Current readiness:** NOT READY for Sprint 2+ feature work  
**Next executable milestone:** M0 — Foundation and Contract Gate

This document turns the PRD and the frontend/backend plans into an ordered,
testable execution queue. The PRD remains the product source of truth. This
file is the delivery source of truth until the M0 gate is passed.

---

## 1. Executive Decision

The product direction is coherent, but the implementation is still a scaffold:

- the frontend is the default Create Next App page;
- the backend exposes only `/health`;
- API routers contain comments but no endpoint implementations;
- every extraction and analysis service is a TODO-only module;
- there are no domain models, database models/migrations, worker tasks, tests,
  fixtures, Docker Compose stack, CI workflow, or shared API contract;
- the PRD is still marked `Draft for Engineering Review`.

Do not start linguistic or traceability features yet. First complete M0 and M1
below. The first useful product slice is one native-text PDF or DOCX uploaded,
stored, extracted asynchronously, and visible in the document list with a
stable API contract.

---

## 2. Readiness Audit

| Area | Document intent | Repository evidence | Status |
|---|---|---|---|
| Product scope | P0 upload, scan, review, export, F10-F13 | PRD is detailed but still Draft | AMBER |
| Frontend | Dashboard, upload, document/review routes | Only default `src/app/page.tsx` | RED |
| API | `/api/v1` document, issue, dictionary, registry endpoints | Routers are empty and not registered | RED |
| Extraction | PDF/DOCX text, layout, tables, headings | `extract.py` contains TODOs only | RED |
| Persistence | PostgreSQL + immutable audit log | No models, session layer, or migrations | RED |
| Async processing | Celery + Redis, isolated stage failures | No Celery app/tasks or result persistence | RED |
| Quality | Unit, integration, component, E2E tests | No project test suites or fixtures | RED |
| Local platform | Docker Compose for Postgres/Redis/LanguageTool | No Compose or `.env.example` | RED |
| Tooling | lint/type/test/build gates | Frontend lint passes; build verification was blocked by an existing `.next/lock`; backend venv could not execute in the current sandbox | AMBER |
| Repository layout | One coordinated product repository | Git metadata currently exists under `frontend/`, not at the product root | RED |

### Blocking design gaps resolved by this plan

1. **Canonical pagination:** `python-docx` and Mammoth do not provide reliable
   rendered pages or bounding boxes. DOCX must be converted to a canonical PDF
   in the worker (LibreOffice headless), while `python-docx` supplies structural
   tables/styles. Review coordinates and page numbers always target the
   canonical PDF.
2. **Coordinate contract:** all PDF boxes use points in a top-left coordinate
   system: `{page_index, x0, y0, x1, y1, page_width, page_height}`. API page
   indexes are zero-based; human-facing page labels are separate fields.
3. **Pipeline transport:** never send a full extraction object through Redis.
   Persist an extraction artifact and pass `{document_id, artifact_uri}` between
   Celery tasks.
4. **Partial failure:** document status is one of `QUEUED`, `PROCESSING`,
   `COMPLETED`, `COMPLETED_WITH_WARNINGS`, or `FAILED`. A stage failure is stored
   explicitly and does not erase successful findings.
5. **Contract vocabulary:** API values are uppercase enums
   (`LINGUISTIC`/`TRACEABILITY`); query parameters may be case-insensitive but
   responses are canonical uppercase.
6. **MVP input boundary:** native-text PDF and DOCX are release-blocking. OCR is
   best-effort behind a feature flag and cannot be used to claim F10/F11 metric
   targets.
7. **MVP security boundary:** authentication/RBAC is required before a shared or
   production deployment. Local single-user development may use an explicit
   `AUTH_MODE=disabled` setting.

---

## 3. Fixed Technical Decisions for Agent Execution

Agents should use these defaults unless a product owner changes the PRD:

| Decision | Selected default |
|---|---|
| Runtime | Python 3.13.15; Node 24.20.0 LTS; pin the same versions in CI |
| Frontend | Existing Next.js 16 App Router project; follow local Next docs |
| API | FastAPI under `/api/v1`; OpenAPI is the canonical FE/BE contract |
| Database | PostgreSQL + SQLAlchemy async + Alembic |
| Jobs | Celery + Redis; chord/group after shared extraction |
| Files | Storage interface; local filesystem in dev, S3-compatible adapter later |
| Review rendition | Canonical PDF for both PDF and DOCX uploads |
| Identifiers | UUID v4 generated server-side |
| Timestamps | UTC ISO-8601 at API boundaries |
| Numeric math | `Decimal`, never binary float; store value, unit, and precision |
| API errors | RFC 9457-style problem details with stable application error code |
| Testing | pytest/httpx; Vitest + Testing Library; Playwright for E2E |
| Contract generation | Export OpenAPI JSON and generate frontend types from it |
| Design source | Stitch project via MCP; checked-in `docs/design_system.md` snapshot |

The installed dependencies must be reconciled during M0. The current backend
requirements omit planned packages such as `pdfplumber`, `pyspellchecker`, test
tooling, and XLSX/PDF export tooling. Install only dependencies needed by the
active milestone; do not install the entire future stack pre-emptively.

---

## 4. Target Domain Contracts

Define these before feature logic so every service and UI task shares one model.

### 4.1 Core records

- `Document`: id, original filename, safe filename, media type, byte size,
  SHA-256, storage URI, canonical PDF URI, status, progress, timestamps.
- `StageRun`: id, document id, stage name, status, progress, error code,
  sanitized error message, started/finished timestamps, artifact URI.
- `ExtractionArtifact`: schema version, document metadata, pages, spans,
  headings, tables/cells, text anchors, warnings.
- `Issue`: common fields plus a typed `evidence` object. Do not keep expanding
  nullable top-level fields for every issue type.
- `IssueDecision`: decision, optional edited value/comment, actor, timestamp,
  optimistic-lock version.
- `AuditEvent`: append-only actor/action/target/before/after/timestamp record.

### 4.2 Required invariants

- File bytes and SHA-256 are immutable after upload.
- A document may be retried, but every scan attempt gets new `StageRun` rows.
- Issue evidence includes `extractor_version` and `rule_version`.
- Traceability issues cannot be bulk accepted.
- Approved documents cannot mutate old audit events or dispositions; changes
  append a new event/version.
- Filenames are display metadata only and never used as storage paths.
- Every response model has an example and is covered by an API contract test.

---

## 5. Ordered Execution Queue

Only start a ticket when all dependencies are complete. Each ticket should be a
small PR/commit with its own tests. Do not combine milestone gates with later UI
or NLP features.

### M0 — Foundation and Contract Gate

#### M0.1 Normalize repository and runtime

**Status:** COMPLETE (2026-09-04)

**Files:** product-root Git/config, `.gitignore`, `.editorconfig`, runtime version
files, `README.md`  
**Work:** establish one product repository boundary; exclude venvs, `.next`,
uploads, generated artifacts, and secrets; standardize backend environment as
`.venv`; document exact Node/Python versions. Preserve existing history when
normalizing the current nested frontend repository.  
**Tests:** clean fresh-install commands documented and repeatable.  
**Done when:** `git status` from product root works and generated/runtime files
are not tracked.

**Evidence:** product-root `main` now contains `backend/`, `frontend/`, and
`docs/`; the former frontend commit is retained as merge ancestry; `frontend`
is a normal tracked tree rather than a gitlink; root ignore/attribute/editor
rules are present; Node.js and Python versions are pinned.

#### M0.2 Approve MVP decisions and acceptance corpus plan

**Status:** COMPLETE (2026-09-04) — all proposed defaults owner-approved

**Files:** `docs/Document_QC_WebApp_PRD.md`, new `docs/acceptance_matrix.md`  
**Work:** change PRD status only after owner approval; record native-text input
boundary, canonical DOCX rendering, RBAC release boundary, retention limits,
max pages/files per batch, and export formats. Define labeled truth sets and the
formula/denominator for every success metric.  
**Tests:** document review checklist; no code.  
**Done when:** no P0 behavior depends on an unresolved product choice.

**Evidence:** `docs/acceptance_matrix.md` defines proposed input/retention/export
boundaries, labeled corpus composition, exact metric formulas, functional
release scenarios, and an explicit owner-approval checklist.

#### M0.3 Create the backend domain and API contract

**Status:** COMPLETE (2026-09-04)

**Files:** `backend/domain/`, `backend/schemas/`, router response models,
`openapi.json` generation script  
**Work:** implement enums and models from section 4, problem details, pagination,
filtering, and examples. Register routers even when later operations return an
explicit `501 FEATURE_NOT_READY`.  
**Tests:** OpenAPI snapshot and Pydantic validation tests.  
**Done when:** frontend types can be generated without hand-written duplicate
interfaces.

**Evidence:** strict domain/API schemas, typed issue evidence, canonical
coordinate models, optimistic-lock request fields, registered `/api/v1`
routers, RFC-style problem responses, an exported `backend/openapi.json`, and
contract smoke tests are present. Ruff passed, strict mypy passed across 22
source files, and all 5 contract tests passed in the audit environment.

#### M0.4 Add executable quality gates

**Status:** COMPLETE locally (2026-09-04); remote CI confirmation pending push

**Files:** backend and frontend test configs, CI workflow, lint/type configs  
**Work:** add pytest/httpx, Ruff, mypy/pyright, Vitest/Testing Library, and build
checks. Avoid fake coverage thresholds until meaningful code exists.  
**Tests:** intentionally failing smoke check proves each CI job runs; restore it
before merge.  
**Done when:** one command per app runs lint, typecheck, test, and build.

**Evidence:** backend has Ruff, strict mypy, pytest, a single PowerShell quality
script, and contract tests; frontend has ESLint, `tsc --noEmit`, Vitest, build,
and a combined `npm run check`; GitHub Actions runs both jobs and verifies that
generated OpenAPI/frontend contract snapshots are current.

#### M0.5 Connect and baseline Stitch MCP

**Status:** COMPLETE (2026-09-04) — endpoint enabled and authenticated

**Depends on:** M0.1; blocks M1.5 and M3 frontend work only  
**Files:** local MCP configuration (never committed), `docs/design_system.md`,
`docs/design_handoff.md`  
**Work:** connect the agent to the selected Stitch project; keep the Stitch API
key in the user's MCP/secret configuration; verify project and screen access;
extract design tokens, typography, spacing, breakpoints, component states, and
screen identifiers into a versioned snapshot. Record the Stitch project/screen
IDs and snapshot date, but never the credential.  
**Tests:** the agent can list the intended project and fetch the chosen screens;
token values in the snapshot match Stitch; a browser screenshot comparison is
defined for dashboard, upload, processing, and review states.  
**Done when:** frontend agents can implement a named Stitch screen without
guessing tokens or relying on an unversioned chat response.

**Current evidence:** local Codex configuration lists `stitch` at the expected
remote MCP endpoint with status enabled. The current task has no callable
Stitch tools and the local MCP status reports unauthenticated, so project/screen
listing has not passed yet. Rotate the exposed credential, authenticate through
the Codex MCP UI, and open a fresh task before re-running this gate.

Stitch is a design-time dependency, not an application runtime dependency. Its
MCP output controls visual composition and tokens; the PRD controls behavior,
accessibility, and product scope; OpenAPI controls data. If they conflict, stop
and record the conflict in `docs/design_handoff.md` instead of silently changing
business behavior to match a mockup.

**M0 gate:** approved contract, one repository boundary, reproducible runtimes,
and green empty/smoke quality pipeline. Stitch access may remain pending for
backend work, but must pass M0.5 before the first frontend lifecycle ticket.

### M1 — Upload-to-Extraction Vertical Slice

#### M1.1 Infrastructure and persistence

**Status:** IMPLEMENTED locally — PostgreSQL/Redis integration pending Docker installation

**Depends on:** M0  
**Files:** `compose.yaml`, `backend/.env.example`, DB/session modules, Alembic
migration  
**Work:** Postgres and Redis health checks; document/stage-run tables; local
storage adapter; upload directory bootstrap.  
**Tests:** migration upgrade/downgrade in an ephemeral DB; storage adapter unit
tests.  
**Done when:** a fresh checkout can start dependencies and migrate once.

**Evidence:** Compose services and health checks, environment template, async
SQLAlchemy session, document/stage-run models, initial Alembic migration, and an
atomic immutable local-storage adapter are implemented. Ruff and strict mypy
pass across 32 files; 16 tests and offline PostgreSQL migration generation
pass. Container startup and live upgrade/downgrade remain unverified because
Docker is not installed on the current machine.

#### M1.2 Secure upload API

**Status:** COMPLETE locally (2026-09-04)

**Depends on:** M1.1  
**Files:** `backend/api/documents.py`, upload service  
**Work:** stream uploads; enforce byte limit; verify MIME and magic bytes; allow
PDF/DOCX only; sanitize display name; hash content; persist atomically; reject
empty, malformed, duplicate-in-flight, and DOCX zip-bomb inputs.  
**Tests:** valid PDF/DOCX plus wrong extension, wrong signature, oversize, empty,
path traversal, and malformed ZIP cases.  
**Done when:** upload returns `201` with a persisted `QUEUED` document.

**Evidence:** API accepts secure document ingestion, handles deduplication, and returns proper status codes. Locally committed but not pushed.

#### M1.3 Versioned Extraction Service (PDF/DOCX)

**Status:** COMPLETE (2026-09-04) — extraction pipeline implemented

**Depends on:** M1.1; blocks M2.1  
**Files:** `backend/services/extract.py`, `backend/schemas/extraction.py`  
**Work:** PDF text/spans/headings/tables; DOCX structure; headless DOCX-to-PDF
conversion; text-anchor mapping; warnings for unsupported/encrypted inputs.
Keep format adapters separate from the normalized artifact model.  
**Tests:** golden JSON fixtures for at least one PDF and one DOCX; coordinate
bounds and deterministic output assertions.  
**Done when:** the same logical sample yields a versioned artifact with stable
pages, text anchors, and tables.

#### M1.4 Celery orchestration and status API

**Depends on:** M1.1, M1.3  
**Files:** Celery app/tasks, status endpoint, retry policy  
**Work:** upload queues extraction after DB commit; tasks pass artifact URIs;
persist stage progress and sanitized failures; make retries idempotent.  
**Tests:** eager-mode task tests plus Redis-backed integration smoke test.  
**Done when:** state transitions and `COMPLETED_WITH_WARNINGS` behavior match the
contract.

#### M1.5 Minimal frontend lifecycle

**Depends on:** M0.3, M0.5, M1.2, M1.4  
**Files:** providers, generated API types/client, dashboard, upload page,
document detail/status components  
**Work:** implement the named Stitch screens using the versioned token snapshot;
add accessible upload, error states, polling with backoff, document list, and
per-stage progress. No split-screen or mock issue data yet.  
**Tests:** component tests for upload/status states; Playwright happy path.  
**Done when:** a user completes Upload → Processing → Extracted from the UI.

**M1 gate:** native-text PDF and DOCX pass the vertical slice in a clean local
environment; malformed inputs fail safely; all quality commands are green.

### M2 — Deterministic Traceability Core

Prioritize audit-critical deterministic rules before the noisier linguistic
pipeline, but implement them one vertical slice at a time:

1. **M2.1 Revision sync:** filename, cover, and revision-table extraction;
   normalize revision tokens; emit evidence-rich mismatches.
2. **M2.2 Standard traceability:** registry patterns, body/reference section
   boundaries, normalized code + edition matching.
3. **M2.3 Table math:** `Decimal` parser, units, locale separators, subtotal
   scoping, tolerance policy, stated/computed cell locations.
4. **M2.4 Reference drift:** ToC/LoF/LoT entries, printed-page labels, canonical
   PDF target anchors, roman/arabic sections.
5. **M2.5 Aggregation:** versioned rule output, deduplication, deterministic
   severity mapping, stage-failure issues, persistence.

For each M2 ticket: require correct/mismatch/malformed fixtures, property tests
for parsers, false-positive assertions, and an API integration test. A failed
analyzer must not prevent other analyzer results from being stored.

**M2 gate:** F10-F13 pass the labeled native-text corpus and publish measured
precision/recall/accuracy with corpus version and rule version.

### M3 — Review and Audit Workflow

1. Read-only canonical PDF viewer with stable page navigation.
2. Language/Traceability issue tabs, filters, virtualization, and deep links.
3. Single- and dual-location highlight overlays using normalized coordinates.
4. Optimistically locked issue decisions and comments.
5. Lead Reviewer dispositions and append-only audit events.
6. Authentication/RBAC before shared deployment.
7. Keyboard and screen-reader flows; no color-only severity semantics.

**M3 gate:** two concurrent reviewers cannot silently overwrite each other;
traceability bulk acceptance is impossible in API and UI; audit history is
append-only.

### M4 — Linguistic Pipeline

Implement spelling, duplicate detection, grammar, and ambiguity independently.
Run LanguageTool as an optional/degraded external stage. Add dictionary
governance before claiming the `<5%` domain-term false-positive target. Tune
only against a held-out corpus and record disabled rules/versioning.

**M4 gate:** every analyzer has a timeout, deterministic normalized output,
error isolation, and measured false-positive results.

### M5 — Export, Hardening, and Release

1. XLSX issue log with separate sheets and immutable evidence fields.
2. Annotated PDF using canonical coordinates; never silently change
   traceability data.
3. DOCX tracked-change export only if separately approved and technically
   validated; `python-docx` alone does not create true Word tracked changes.
4. Retention/deletion jobs, malware scanning integration, rate limits, security
   headers, secrets handling, backups, and restore test.
5. Performance budgets for 20-page and maximum-size samples.
6. Full Playwright flow and release runbook.

**M5 gate:** Upload → Scan → Review → Export passes E2E; P0 metrics are measured,
not estimated; security and recovery checks pass.

---

## 6. Agent Work Protocol

Every agent task must include this compact contract:

```text
Ticket: Mx.y and one-sentence outcome
Read first: exact PRD/plan sections and local AGENTS.md
Allowed scope: explicit files/directories
Inputs/outputs: schemas or endpoint contract
Edge cases: named list
Tests required: exact commands and fixture names
Definition of done: observable behavior
Non-goals: later milestone work
```

Execution loop:

1. Inspect the current files and preserve unrelated user changes.
2. Restate the ticket's observable outcome and dependencies.
3. Add/update the smallest failing test or contract snapshot.
4. Implement the narrow vertical behavior; avoid speculative abstractions.
5. Run focused tests, then the milestone quality commands.
6. Compare actual output with the contract and fixtures.
7. Update this queue: evidence, remaining risks, and next unblocked ticket.

An agent must not mark a ticket complete based only on compilation, placeholder
responses, mocked UI data, or TODO comments. Completion requires the ticket's
observable behavior and named tests.

---

## 7. Immediate Next Actions

Execute in this exact order:

1. M0.1 — normalize repository/runtime boundaries. Repository flattening and
   local runtime pins were completed on 2026-09-04; CI enforcement remains part
   of M0.4.
2. M0.2 — obtain product-owner decisions and freeze the MVP acceptance matrix.
3. M0.3 and M0.4 — domain/OpenAPI contract and quality pipeline may proceed in
   parallel after M0.1.
4. M0.5 — connect Stitch MCP and freeze the first design snapshot before
   frontend implementation.
5. Run the M0 gate review.
6. Start M1.1 and M1.3 in parallel; integrate through M1.2/M1.4.
7. Finish M1.5 and run the first vertical-slice demo with visual comparison to
   the approved Stitch screens.

Do not assign Sprint 2/Sprint 3 feature modules until M1 passes. Their current
TODO stubs are useful filenames, not evidence that foundation work is complete.
