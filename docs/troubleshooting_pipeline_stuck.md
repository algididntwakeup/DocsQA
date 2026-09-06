# Troubleshooting Guide: Backend Pipeline Extraction Issues

> **Status (2026-09-06)**: All bugs below are **FIXED** (commits `3fcc885`,
> `0b060b3`). This doc is preserved as an incident post-mortem and quick
> reference. If extraction hangs again, jump to Section 3 (Immediate Workaround).

---

## 1. Fixed Bugs & Root Causes

### Bug 1 â€” `TypeError: 'float' object is not subscriptable` âœ… FIXED `0b060b3`

**File**: `backend/services/extract.py`, table cell iteration loop.

**Root cause**: `Table.cells` in PyMuPDF is a **flat** `list[tuple(x0,y0,x1,y1)]`
of all cell bounding boxes â€” one 4-tuple per cell. It is **NOT** a 2D rowÃ—col
grid. The old code iterated it as a grid:

```python
for row_idx, row in enumerate(table.cells):      # row = (x0, y0, x1, y1)
    for col_idx, cell_rect in enumerate(row):    # cell_rect = float (one coord!)
        if cell_rect[2] <= cell_rect[0]: ...     # TypeError: float not subscriptable
```

**Fix**: Use `table.rows` â†’ `TableRow.cells` for proper 2D row-major iteration:

```python
finder = page.find_tables()
for table in finder.tables[:_MAX_TABLES_PER_PAGE]:
    for row_idx, table_row in enumerate(table.rows):
        for col_idx, cell_rect in enumerate(table_row.cells):
            if cell_rect is None:        # merged/spanned cell
                continue
            x0, y0, x1, y1 = float(cell_rect[0]), float(cell_rect[1]), ...
```

---

### Bug 2 â€” Celery worker stuck forever âœ… FIXED `3fcc885`

**File**: `backend/tasks/extraction.py`

**Root cause**: Task had no `soft_time_limit` / `time_limit`. `autoretry_for=(Exception,)`
re-queued the task when it timed out, blocking the worker indefinitely.

**Fix**:
- Added `soft_time_limit=180`, `time_limit=240` to the task decorator.
- Removed `autoretry_for`.
- Added `SoftTimeLimitExceeded` handler â†’ marks document `COMPLETED_WITH_WARNINGS`.

---

### Bug 3 â€” SSE `/events` endpoint not real-time âœ… FIXED `3fcc885`

**File**: `backend/api/documents.py`

**Root cause**: `event_generator()` emitted one snapshot then closed; the frontend
EventSource reconnected endlessly with no live progress.

**Fix**: `event_generator()` is now an `asyncio` loop polling the DB every 2 s
until terminal status, then emits `event: close`.

---

### Bug 4 â€” PyMuPDF CAD table matrix explosion âœ… FIXED `3fcc885`

**File**: `backend/services/extract.py`

**Root cause**: Dense CAD linework produces 30 000+ phantom table cells.
`get_text(clip=...)` per cell blocks the Celery worker indefinitely.

**Fixes**:
- 20 s per-page monotonic timeout (skip table extraction if text phase overran).
- Max 20 tables per page (`_MAX_TABLES_PER_PAGE`).
- Skip any table > 500 cells / 100 rows / 30 cols.
- Defensive `float()` unpack + degenerate-bbox skip.

---

## 2. Architecture Reference

```
POST /upload
  â†’ save file, create Document(status=UPLOADING)
  â†’ dispatch Celery task: docqc.extract

[Celery Worker â€” docqc.extract]
  â†’ PDFExtractor.extract(file_path)
  â†’ per page (20 s budget):
      page.get_text("blocks")        â†’ text spans + bboxes
      page.find_tables()             â†’ TableFinder
      finder.tables[:20]             â†’ capped list[Table]
      table.rows                     â†’ list[TableRow]  â† correct 2D API
      table_row.cells                â†’ list[tuple|None]
  â†’ persist extraction.json to artifacts/{doc_id}/
  â†’ run analyzers: revision_sync, ref_drift, table_math, â€¦
  â†’ update Document.status = COMPLETED

GET /api/v1/documents/{id}/events   (SSE)
  â†’ polls DB every 2 s while PROCESSING
  â†’ emits: event: progress / data: {status, progress_pct, stages}
  â†’ emits: event: close when terminal
```

### PyMuPDF API Quick Reference

| Attribute | Type | Notes |
|---|---|---|
| `page.find_tables()` | `TableFinder` | Do not iterate directly; use `.tables` |
| `TableFinder.tables` | `list[Table]` | âœ… Correct way to get table list |
| `TableFinder.cells` | `list[tuple]` | Flat list of ALL cells across ALL tables |
| `Table.cells` | `list[tuple]` | âŒ Flat list of bbox tuples â€” NOT 2D grid |
| `Table.rows` | `list[TableRow]` | âœ… Use for row-major 2D iteration |
| `TableRow.cells` | `list[tuple\|None]` | One per column; `None` = merged cell |
| `Table.bbox` | `tuple(x0,y0,x1,y1)` | Bounding box of the whole table |

---

## 3. Immediate Workaround (if a document is stuck)

```bash
# Check what worker is doing
docker compose logs --tail=50 worker

# Restart worker to kill a hung task
docker compose restart worker

# Mark stuck document as FAILED (if it stays PROCESSING after restart)
docker compose exec -T postgres psql -U docsqa -d docsqa -c "
UPDATE documents
SET status = 'FAILED'
WHERE status = 'PROCESSING' AND updated_at < NOW() - INTERVAL '10 minutes';
"
```

---

## 4. Verification Checklist

```powershell
# Backend quality gate (197 tests must pass, 0 ruff/mypy errors)
powershell -ExecutionPolicy Bypass -File backend\scripts\quality.ps1

# Rebuild worker in Docker and upload a test PDF
docker compose up -d --build worker
docker compose logs -f worker
# â†’ should NOT see "float object is not subscriptable"
# â†’ should complete in < 4 minutes for a normal engineering PDF
# â†’ complex CAD PDFs reach COMPLETED_WITH_WARNINGS within 4 minutes
```

