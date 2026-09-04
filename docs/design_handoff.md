# Stitch Design Handoff Log

**Status:** COMPLETE (2026-09-04)

Use this append-only log to connect a named Stitch screen to an implementation
ticket and browser verification evidence. Never record Stitch API keys.

## Handoff Template

```text
Ticket: M1.5 Minimal frontend lifecycle
Stitch project ID: 9978725055094825738
Stitch screen ID/name:
- fd821940390e47898c54e85c8a4765b2 (MatQC Industrial Logo)
- 710cf0fc0e3b4f07a8a063764b5420a4 (Active Document QC Inspection)
- 78e00f74aa8d4baab07ed9448febeff7 (Active Document QC Inspection (Light Mode))
- 6edbc1734a05464481cee22e2c96387d (Active Document QC Inspection - Specialized Error Panels)
Fetched at (UTC): 2026-09-04
Design snapshot commit: `d0b6370`
Target route/components: `/`, `/upload`, `/documents/[id]`; AppShell,
Dashboard, DocumentList, DropZone, UploadWorkspace, DocumentStatusView,
ScanProgress
Required responsive states: desktop instrument shell, compact rail below
1000px, bottom navigation and single-column content below 680px
Required loading/empty/error states: dashboard loading/empty/API error; upload
validation/per-file success/error; status loading/API error/terminal outcome
Known PRD/OpenAPI conflicts: none for the M1.5 lifecycle scope
Resolution owner:
Browser viewport evidence: Playwright Desktop Chrome happy path
Implementation commit: `16fd31f`
```

## Conflict Rule

- PRD controls behavior, roles, security, and accessibility.
- OpenAPI controls data shapes and error states.
- Stitch controls visual layout and styling.
- An unresolved conflict blocks the affected UI ticket, not unrelated backend
  work. Record it here instead of silently guessing.
