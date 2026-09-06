# Troubleshooting Guide: Backend Pipeline Hangs & Long-Running Extraction Tasks

This guide provides technical diagnosis, root cause analysis, immediate workarounds, and step-by-step remediation instructions for future agents and engineers when the document extraction pipeline appears stuck or hangs indefinitely in `PROCESSING`.

---

## 1. Symptoms & Incident Signature

### User-Visible Symptoms
- A newly uploaded document remains in `status: "PROCESSING"` with `progress_pct` frozen (often at `10%` to `25%`).
- Server-Sent Events (SSE) `/api/v1/documents/{id}/events` emit no progress updates for minutes or hours.
- Inspection register dashboard shows ongoing spinners without transition to `COMPLETED` or `FAILED`.

### Celery Worker Logs
When inspecting logs via `docker compose logs -f worker`, the worker output exhibits repetitive warnings:
```text
[WARNING/ForkPoolWorker-1] Error extracting table cell 2526,0: arg=...
[WARNING/ForkPoolWorker-1] Error extracting table cell 2527,0: arg=...
[WARNING/ForkPoolWorker-1] Error extracting table cell 2528,0: arg=...
```
The row numbers climb into thousands (`row_idx > 2000`), with the CPU pegged at 100% on one core.

---

## 2. Root Cause Analysis (RCA)

### A. PyMuPDF `find_tables()` on Dense Engineering Vector Drawings
In `backend/services/extract.py` (`PDFExtractor.extract`):
```python
# Extract tables using PyMuPDF's find_tables
tables = page.find_tables()
for table in tables:
    ...
    if table.cells:
        for row_idx, row in enumerate(table.cells):
            for col_idx, cell_rect in enumerate(row):
                ...
                cell_text = page.get_text("text", clip=cell_rect).strip()
```

- **Pathological Input**: PDFs containing CAD drawings, architectural blueprints, cross-hatching, engineering diagrams, or dense vector line work contain thousands of intersecting paths.
- **Table Matrix Explosion**: PyMuPDF's heuristic table finder interprets overlapping vector lines as a massive table matrix (e.g., 3,000 rows x 10 columns = 30,000 cells).
- **Synchronous Cell Clipping Overhead**: For every cell in that matrix, `page.get_text("text", clip=cell_rect)` is executed synchronously. Executing 30,000 text extractions per page on complex vector geometry takes tens of minutes or freezes the Python GIL.
- **Inverted / Degenerate Coordinates**: Intersecting vector lines often produce degenerate or inverted bounding boxes (`x0 >= x1` or `y0 >= y1`), causing PyMuPDF to throw exceptions. The exception handling logs each warning, adding I/O and locking overhead.

### B. Lack of Celery Timeouts & Circuit Breakers
In `backend/tasks/extraction.py`:
- `@celery_app.task(name="extract_document_structure")` has **no `soft_time_limit` or `time_limit`** configured.
- As a consequence, a single worker fork pool process remains locked on a pathological page indefinitely, blocking subsequent tasks in the queue.

---

## 3. Immediate Workaround (Manual Operations)

If a document is currently stuck in local Docker or production:

### 1. Identify Stuck Worker Process
```bash
docker compose logs --tail=50 worker
```

### 2. Restart Celery Worker to Terminate Hung Task
Restarting the worker container frees the hung process:
```bash
docker compose restart worker
```

### 3. Mark Stuck Document as FAILED (Optional DB Cleanup)
If the document remains in `PROCESSING` after restarting:
```bash
docker compose exec -T postgres psql -U docsqa -d docsqa -c "
UPDATE documents 
SET status = 'FAILED' 
WHERE status = 'PROCESSING' AND updated_at < NOW() - INTERVAL '10 minutes';
"
```
Or delete the document using the UI **Delete** button or `DELETE /api/v1/documents/{document_id}`.

---

## 4. Remediation Playbook: What To Do Next (For the Next Agent)

When implementing the permanent fix in the backend, follow these 4 steps:

### Step 1: Add Table & Cell Bounding Thresholds in `backend/services/extract.py`
In `PDFExtractor.extract` (around lines 94–148):
1. **Cap Table Count**: Limit `tables` processed per page (e.g., `tables = page.find_tables()[:15]`).
2. **Cap Cell Count**: Before iterating through `table.cells`, inspect dimensions:
   ```python
   num_rows = len(table.cells) if table.cells else 0
   num_cols = len(table.cells[0]) if (num_rows > 0 and table.cells[0]) else 0
   total_cells = num_rows * num_cols

   # Guard against CAD cross-hatching table explosion:
   if total_cells > 600 or num_rows > 300 or num_cols > 30:
       logger.warning(
           "Skipping pathological table on page %s with %s rows and %s columns (%s cells)",
           page_index,
           num_rows,
           num_cols,
           total_cells,
       )
       continue
   ```
3. **Validate Cell Rect Coordinates Before Extraction**:
   Ensure `cell_rect` is valid before passing to `get_text`:
   ```python
   if not cell_rect or cell_rect[2] <= cell_rect[0] or cell_rect[3] <= cell_rect[1]:
       continue
   ```

### Step 2: Implement Page-Level Extraction Timeout
Add a deadline per page:
```python
import time

PAGE_TIMEOUT_SECONDS = 15.0

start_page_time = time.monotonic()
for page_index, page in enumerate(doc):
    if time.monotonic() - start_page_time > PAGE_TIMEOUT_SECONDS:
        logger.warning("Page %s extraction exceeded timeout threshold; proceeding with partial spans.", page_index)
        break
```

### Step 3: Configure Celery Task Time Limits in `backend/tasks/extraction.py`
Decorate `extract_document_structure` with timeouts:
```python
from celery.exceptions import SoftTimeLimitExceeded

@celery_app.task(
    name="extract_document_structure",
    bind=True,
    soft_time_limit=180,  # 3 minutes soft limit
    time_limit=240,       # 4 minutes hard limit
    autoretry_for=(),     # Do not auto-retry timeouts
)
def extract_document_structure(self, document_id: str) -> dict[str, Any]:
    try:
        # Run extraction pipeline...
    except SoftTimeLimitExceeded:
        logger.error("Document %s extraction exceeded soft time limit.", document_id)
        # Update stage run to FAILED or SUCCEEDED_WITH_WARNINGS
        # Update document status to COMPLETED_WITH_WARNINGS
        ...
```

### Step 4: Graceful Degradation to `COMPLETED_WITH_WARNINGS`
If a table extraction fails or times out:
- Do not fail the entire document if raw text spans are already available.
- Emit a stage status of `SUCCEEDED_WITH_WARNINGS` with an issue record category `TABLE_DATA` or system warning.
- Allow the user to view the canonical PDF and remaining document sections in the Review Workspace.

---

## 5. Verification Checklist

After applying the changes above, verify:
1. `pytest backend/tests/test_extract.py -v` passes.
2. An engineering drawing PDF with dense vector linework finishes extraction in < 15 seconds instead of hanging.
3. No infinite loops or repetitive `Error extracting table cell X,Y` logs appear in Celery.
4. `powershell -ExecutionPolicy Bypass -File backend\scripts\quality.ps1` completes with zero errors.
