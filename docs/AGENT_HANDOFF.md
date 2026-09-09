# Agent Handoff

This file records implementation decisions that must not be reverted or duplicated by future agents. Read it after `docs/START_HERE.md` before changing the review pipeline or workspace.

## Current State

- The product is a deterministic engineering-document review tool. Do not introduce LLM, external AI, approval, disposition, or audit-trail workflows.
- Findings use binary report curation: `included_in_report` plus an optional `reviewer_note`.
- The canonical pipeline stages are `EXTRACTING`, `LAYOUT_INSPECTION`, `BUDINSKI_AUDIT`, `STANDARDS_CHECK`, `LINGUISTIC_CHECK`, and `AGGREGATING`.
- `STANDARDS_CHECK` is skipped for external standards packs until a licensed, governed rulebook exists. Internal citation and bibliography checks remain active.

## Budinski Contract

- `backend/services/budinski_evaluator.py` contains the deterministic 41-item evaluator.
- `backend/schemas/budinski.py` contains `EvaluationContext`, `ScorecardEntry`, `BudinskiScorecard.items`, `baseline_score`, and `group_averages`.
- The 41 canonical items are distributed as Group I (9), Group II (11), Group III (11), and Group IV (10).
- Group III rules include purpose, report format, referenced work, standards citations, and repeatable detail. Group IV rules include conclusion clarity, reference attribution, and sentence/paragraph length.
- Legacy grouped scorecard fields remain for compatibility. Do not remove them unless all persisted artifacts and export fixtures have migrated.
- Legacy aliases such as `format_stated`, `adequate_detail_to_repeat`, and `layout_and_whitespace` may be accepted by compatibility dispatch, but must not create duplicate canonical items.

## Export Contract

- `backend/services/export.py` must render scorecard details from `BudinskiScorecard.items` when flat items are present.
- Group averages and baseline values must come from the scorecard's computed data, not document-specific constants or sample-report prose.
- Legacy grouped scorecards are still supported for existing fixtures and persisted data.
- `backend/services/docx_styler.py` owns reusable XML styling primitives: cell shading,
  cell margins, full-width callouts, repeating table headers, and document defaults.
- `backend/services/report_synthesizer.py` owns deterministic executive narrative synthesis
  for summary judgement, bottom line, baseline rows, blockers, major findings, language
  rows, demonstration rewrite, and praise. It must not call external AI or LLM services.
- Production DOCX export in `backend/api/documents.py` adapts persisted issues and
  `artifacts/{document_id}/budinski_scorecard.json` through
  `assessment_from_document_findings()` and then calls `generate_ale_review_docx()`.
- The executive DOCX has ten narrative sections: title/metadata, summary/bottom line,
  baseline measures, blockers, next revision actions, language/mechanics, demonstration
  rewrite, Budinski scorecard, praise, and limits/REVIEWSCORE.
- `backend/services/report.py` remains a compatibility builder for existing direct callers
  and reference-pack tests. Do not route production DOCX export back to its raw findings
  table path without an explicit migration decision.
- Do not reintroduce sample-specific strings such as client names, asset names, dates, component counts, or report identifiers into the export service.
- DOCX export supports `include_minors`; the default remains concise by excluding minor and informational findings from annotated PDF selection unless requested.

## Frontend Workspace Contract

- `frontend/src/components/review/review-workspace-view.tsx` loads all issue pages through `listAllDocumentIssues()` and subscribes to SSE completion events while processing.
- `frontend/src/components/review/split-screen-viewer.tsx` owns the document viewer, issue curation, report preview, dictionary, and export actions.
- The default findings tabs are `Technical & Layout`, `Standards`, and `Language`. `BUDINSKI` and `LAYOUT` findings belong to the first tab.
- Current workspace status banners cover `QUEUED`, `PROCESSING`, `COMPLETED_WITH_WARNINGS`, and `FAILED` without inventing scorecard data.
- `DocumentRead` currently exposes metadata only. It does not expose the persisted `BudinskiScorecard`; do not add baseline or Group I-IV values to the workspace until a backend endpoint/response contract exposes them.
- Export controls are buttons using `frontend/src/lib/download.ts`, not direct anchor links, so asynchronous download errors can be surfaced consistently.

## Safe Change Rules

- Read `docs/START_HERE.md`, this file, and the relevant source before editing.
- Preserve unrelated worktree changes. Never use destructive reset/checkout commands.
- Regenerate `frontend/src/lib/api-schema.d.ts` only after the backend OpenAPI contract has intentionally changed.
- Do not commit client or sample documents. Local commits are allowed; do not push.
- Run the focused tests for touched areas plus frontend typecheck/lint before committing.

## Verification Snapshot

The latest completed frontend verification is:

```text
npm run typecheck  passed
npm run test       42 passed
npm run lint       passed
```

The focused backend Budinski/export verification must be rerun after changes to the evaluator, schemas, pipeline, or export service.

Latest focused export verification:

```text
55 passed
ruff check passed
git diff --check passed
```
