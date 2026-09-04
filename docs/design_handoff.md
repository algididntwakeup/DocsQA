# Stitch Design Handoff Log

**Status:** WAITING FOR STITCH MCP CONNECTION

Use this append-only log to connect a named Stitch screen to an implementation
ticket and browser verification evidence. Never record Stitch API keys.

## Handoff Template

```text
Ticket:
Stitch project ID:
Stitch screen ID/name:
Fetched at (UTC):
Design snapshot commit:
Target route/components:
Required responsive states:
Required loading/empty/error states:
Known PRD/OpenAPI conflicts:
Resolution owner:
Browser viewport evidence:
Implementation commit:
```

## Conflict Rule

- PRD controls behavior, roles, security, and accessibility.
- OpenAPI controls data shapes and error states.
- Stitch controls visual layout and styling.
- An unresolved conflict blocks the affected UI ticket, not unrelated backend
  work. Record it here instead of silently guessing.
