# PRISM Performance, Complexity, and Anti-Pattern Audit

**Status:** Baseline audit plus staged remediation recorded
**Scope:** `backend/api/`, `backend/services/`, `backend/tasks/`, `backend/models/`, `frontend/src/`
**Audit type:** Static diagnostic audit with source evidence
**Application code changed after baseline:** Yes; see the implementation status below.

## Remediation status

Implemented in the current worktree:

- LibreOffice conversion calls in async document routes now run through Starlette's threadpool helper.
- Managed-user ownership counts use one grouped SQL query.
- Project summaries use document-count aggregates instead of eager-loading every document.
- Reversible performance-index migration `backend/alembic/versions/20261006_0018_performance_indexes.py` adds indexes for document project/owner/workflow filters and project creators.
- Dashboard EventSource subscriptions are keyed by stable active-document IDs and use bounded exponential reconnects.
- Document, project-document, review-finding, and status-summary views use bounded page requests and explicit load-more behavior where applicable.
- SSE progress uses Redis pub/sub wakeups with PostgreSQL snapshots and a bounded polling fallback.
- Independent analyzer computations run with a bounded four-thread executor; stage persistence and aggregation remain sequential.
- Grammar split-word regexes and Budinski context text are cached/precompiled; PyMuPDF handles close deterministically.

Not implemented by design in this pass:

- Full worker-backed export job API. Threadpool containment was selected as the smallest safe cutover.
- Full Celery stage fan-out/chord orchestration. Analyzer computation is parallelized while existing persistence contracts remain sequential.
- Finding-list virtualization. Add only after browser profiling shows DOM/render cost is material.

## 1. Critical Bottlenecks

### P0 — LibreOffice blocks FastAPI's event loop

- `backend/api/documents.py:728-737` calls `convert_docx_to_pdf()` directly from the async document-preview route.
- `backend/api/documents.py:1044-1058` calls the same conversion directly from the async export route.
- `backend/services/export.py:136-141` uses blocking `subprocess.run()` with a 30-second timeout.
- Impact: DOCX preview/export can block the API worker and serialize unrelated requests.

### P0 — Large response and render surfaces

- `frontend/src/lib/api.ts:369-405` requests up to 100 documents for project/dashboard views.
- `frontend/src/lib/api.ts:449-458` fetches every issue page concurrently through `listAllDocumentIssues()`.
- `frontend/src/components/review/review-workspace-view.tsx:41-45` loads the complete issue collection before rendering.
- `backend/api/projects.py:220-224` eager-loads every `Project.documents` row for project summaries.
- Impact: database result size, browser memory, React reconciliation, and request fan-out grow with collection size.

### P1 — Per-client SSE database polling

- `backend/api/documents.py:1110-1185` polls `documents` and `stage_runs` every 2 seconds for each SSE connection, up to 10 minutes.
- `frontend/src/components/document/dashboard.tsx:85-99` opens one stream per active document.
- `frontend/src/app/projects/[id]/page.tsx:72-76` also polls every 3 seconds while rows are processing.
- Impact: database polling grows with active clients and active documents. The loop is bounded, but expensive.

### P1 — Serial pipeline execution

- `backend/tasks/extraction.py:653-695` runs independent analyzers sequentially.
- `backend/tasks/extraction.py:715-768` then runs aggregation and review stages in the same task.
- Task limits are 300 seconds soft and 420 seconds hard (`backend/tasks/extraction.py:806-814`).
- Impact: one slow analyzer delays all subsequent stages and increases tail latency.

### P1 — Full artifact retention

- `backend/services/extract.py:163-235` accumulates pages, spans, headings, and tables in one artifact.
- `backend/tasks/extraction.py:604-750` retains the artifact while all analyzers execute and serializes it to JSON.
- `backend/services/duplicate.py:93-128` additionally builds candidates, token sets, and postings.
- `backend/services/grammar.py:155` analyzes original and joined spans.
- Impact: peak RAM grows with document size and duplicated text structures.

### P1 — Missing high-use foreign-key/workflow indexes

- `Document.project_id`, `Document.owner_id`, and `Document.verified_by_id` are foreign keys without explicit indexes.
- `Document.workflow_status` is filtered in list endpoints without an explicit index.
- `Project.created_by_id` is a foreign key without an explicit index.
- Existing indexes cover `documents(status, created_at)`, `assigned_to_id`, issue document/category/severity/page, and project assignment.
- Impact: visibility, dashboard, ownership, and workflow queries can degrade into sequential scans as data grows.

### P1 — Managed-user N+1 query

- `backend/api/auth.py:274-275` loads all users, then calls `_managed_user_read()` once per user.
- `backend/api/auth.py:257-265` executes one document ownership count query per user.
- Complexity: `1 + U` queries for `U` users.

### P1 — Project summary loads full document collections

- `backend/api/projects.py:220-224` uses `joinedload(Project.documents)` for project listing.
- `_project_read()` derives summary values from the loaded collection.
- Impact: project-list cost scales with all documents instead of project count.

### P2 — BIMA network synchronization on project-list requests

- `backend/api/projects.py:208-210` can call `sync_user_bima_projects()` during an engineer's project-list request.
- `backend/services/bima_client.py` uses async `httpx`, so this is not event-loop blocking, but request latency remains coupled to BIMA timeout/availability.

## 2. Code Smells and Spaghetti Flows

- Export orchestration, DOCX rendering, temporary files, LibreOffice conversion, and response bytes are combined in one async HTTP path.
- Preview conversion and export conversion are separate callers of the same blocking operation and can duplicate work.
- Stage names and pipeline status mapping are distributed between `services/pipeline.py`, `tasks/extraction.py`, and SSE serialization.
- One Celery task owns extraction, all analyzers, aggregation, and review audits.
- Compatibility report generation remains alongside production export paths and must be removed only after caller/artifact migration proof.
- Frontend fetch/poll/SSE lifecycle is manually managed across components instead of sharing one cache/subscription abstraction.
- Static grammar regexes are compiled inside span loops (`backend/services/grammar.py:273-275`).
- Budinski helper methods repeatedly reconstruct joined context text.
- Duplicate detection is already guarded by an inverted index, posting cap, length pruning, and `MAX_FUZZY_COMPARISONS = 100_000`; it is bounded but can still be CPU-heavy.

## 3. Doom-Loop Checklist

### Confirmed infinite loops

None found in the inspected paths.

### Bounded loops

- SSE server loop: bounded by `MAX_POLL_DURATION = 600` seconds and terminal status.
- Celery retries: bounded by `max_retries=2`; broad `autoretry_for` was removed.
- PDF page/table loops: finite and guarded by table/page caps and time limits.
- Duplicate fuzzy comparisons: bounded by `100_000` comparisons.

### Frontend reconnect risk

- `frontend/src/components/document/dashboard.tsx:85-99` has an effect dependent on the entire `documents` array.
- Every SSE progress event updates `documents`, which tears down and recreates all active `EventSource` instances.
- `frontend/src/lib/api.ts:668-670` forwards `EventSource.onerror` without an explicit backoff/visibility policy; browser reconnect behavior can amplify outage traffic.
- This is subscription churn and aggressive reconnect behavior, not proven infinite recursion.

## 4. Phased Optimization Roadmap

### Phase 0 — Measure

1. Capture request, SQL, analyzer, artifact-size, and worker-RSS timings.
2. Run `EXPLAIN (ANALYZE, BUFFERS)` on document visibility, project, issue, and user-management queries.
3. Count SSE connections and polling queries.

### Phase 1 — Stabilize API concurrency

1. Move LibreOffice conversion out of async handlers; temporary containment is `run_in_threadpool`, preferred design is worker-backed conversion.
2. Unify preview/export conversion and make it idempotent per document.
3. Replace user-count N+1 with a grouped aggregate.
4. Replace project document collection loading with SQL summary aggregates.
5. Add indexes only after query-plan validation.
6. Stabilize EventSource lifecycle and reconnect behavior.

### Phase 2 — Bound client/server collections

1. Make document and issue pagination effective end-to-end.
2. Avoid `listAllDocumentIssues()` for the review workspace.
3. Add virtualized finding rendering only if measured DOM cost requires it.

### Phase 3 — Reduce progress-polling load

1. Use a shared progress stream or Redis pub/sub fan-out.
2. Keep bounded database fallback for missed events.
3. Pause/retry with backoff for hidden tabs and disconnected clients.

### Phase 4 — Parallelize and slim pipeline work

1. Persist extraction before analyzer fan-out.
2. Run independent analyzers as bounded Celery jobs.
3. Aggregate after a stage barrier.
4. Cache normalized analyzer context and precompile static regexes.
5. Release large temporary structures between stages.

## Refactoring acceptance criteria

- No blocking `subprocess.run()` remains on an async FastAPI request path.
- Admin user listing uses a constant number of SQL statements independent of user count.
- Project summaries do not load every document row merely to calculate counts.
- Dashboard progress events do not recreate every active `EventSource` on every message.
- Document and finding endpoints return bounded pages, and frontend views do not eagerly load all findings.
- Progress delivery remains functional when Redis is unavailable through a bounded fallback.
- Pipeline stage failures remain visible and terminal documents do not remain stuck.
- Existing authorization, report, export, and workflow contracts remain unchanged.
