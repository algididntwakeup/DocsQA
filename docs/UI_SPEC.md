# UI specification

Keep the PDF viewer, findings list, filters, and scan progress. Replace decisions,
dispositions, audit trail, and approval controls with include/exclude and reviewer note
controls. The export panel offers only DOCX review report and annotated PDF.

## Review Workspace

- `ReviewWorkspaceView` loads the document and every issue page, not only the first API page.
- While a document is `QUEUED` or `PROCESSING`, the workspace subscribes to document SSE
  events and refreshes findings after `COMPLETED` or `COMPLETED_WITH_WARNINGS`.
- `FAILED` and `COMPLETED_WITH_WARNINGS` states must be visible before export so reviewers
  understand that findings may be incomplete or require inspection.
- The split workspace contains the PDF viewer on the left and the findings/curation panel
  on the right. On smaller screens it uses a document/findings pane switcher.

## Findings Tabs

- `Budinski & Layout Audit`: `BUDINSKI` and `LAYOUT` categories. This is the default tab because high-priority engineering-document defects are the primary review focus.
- `Standards`: traceability, reference, table-math, and standards-related findings.
- `Language`: linguistic, spelling, grammar, and dictionary findings.
- Findings are sorted by current severity precedence: `BLOCKER`, `CRITICAL`, `MAJOR`,
  `MINOR`, `INFO`, followed by legacy `HIGH`, `MEDIUM`, and `LOW` values.

## Export

- Export actions use asynchronous buttons and `frontend/src/lib/download.ts`.
- DOCX and PDF export accept the `include_minors` query option. It is off by default.
- Do not render Budinski baseline or Group I-IV scorecard numbers in the workspace until
  the API exposes `BudinskiScorecard` data. The current `DocumentRead` response contains
  document metadata only.

## Live Document Progress

- The `/documents` dashboard subscribes to `GET /api/v1/documents/{id}/events` for every
  `QUEUED` or `PROCESSING` document.
- Progress percentage and status badges update from SSE events without a full-page reload.
- A five-second document-list refresh remains enabled as a fallback and to reconcile the
  final terminal response after `COMPLETED`, `COMPLETED_WITH_WARNINGS`, or `FAILED`.
- Active rows show a pulse indicator and animated progress treatment. The dashboard also
  displays a `Live monitoring active` status banner so a long-running extraction is not
  mistaken for a hung browser page.
- If `EventSource` is unavailable or the stream disconnects, the existing polling path
  continues to refresh the register.
