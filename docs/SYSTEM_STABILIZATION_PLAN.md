# System Stabilization — Completed Implementation

## Completed scope

1. Runtime report generation uses the generic extracted-document evaluator. Canonical ALE/MEPG output is isolated to `backend/tests/canonical_ale_fixture.py`; production code no longer selects it from filename or `is_ale_baseline`. Missing identity fields remain `not supplied`, and export narrative uses the actual filename, extracted headings, and finding evidence.
2. PDF.js keeps the active `RenderTask` in a ref, cancels it before replacement and during cleanup, ignores cancellation errors, rejects stale completions, cleans pages and loaded document proxies, and clears stale canvas dimensions. PDF input remains an `ArrayBuffer`; no object URL is created.
3. Claim and assignment routes retain row locking without nullable `joinedload` relationships in `FOR UPDATE` queries, explicitly roll back HTTP and unexpected failures, refresh `owner`/`assigned_to` after commit, and serialize nullable assignment metadata without async lazy loads. Assignment regressions cover first-call success, nullable unassignment, WIP HTTP 400, and commit-failure retry.
4. Project detail polling is page-owned, guarded against overlapping loads, runs every 3000 ms while rows are `QUEUED`, `PROCESSING`, or defensive legacy `ANALYZING`, and stops when all rows are terminal. Human `workflow_status=ANALYZING` remains separate from processing state.
5. Project document rows render `Sedang Dianalisis...` with progress and a disabled workspace button during processing. Terminal rows render `/documents/{id}/review` as `Buka Workspace`. Legacy serialized `ANALYZING` is covered by the table regression test.

## Verification record

- Backend modified modules and tests compile with `python -m py_compile`.
- Backend focused pytest was attempted with `python -m pytest tests/test_kanban_assignment.py tests/test_report.py -q`, but this environment has no `pytest` module installed.
- Frontend TypeScript passed with `npx tsc --noEmit --pretty false`.
- Frontend full Vitest passed: 16 files, 52 tests.
- Changed frontend files pass ESLint. Full `npm run lint` remains blocked by pre-existing `react-hooks/set-state-in-effect` errors in `src/components/admin/user-projects-modal.tsx` and `src/components/review/split-screen-viewer.tsx`; unrelated warnings remain in other files.
- Production frontend build passed with `npm run build`.
- Authenticated live project/workspace smoke was unavailable: `http://localhost:3000/projects` redirected to `/login`. No browser claim, upload, or PDF interaction was claimed.

## Release status

The implementation is complete and ready for a local commit. Backend behavioral execution still requires a Python environment with project test dependencies, and authenticated UI smoke requires a logged-in running stack.
