"""
Issue Aggregation Service
============================
Normalizes all linguistic + traceability findings into the unified issues schema:
{issue_id, doc_id, category, type, page, span_or_bbox, original_value,
 expected_value, delta, suggestion, confidence, severity}

Pipeline stage 10 — final aggregation step.
"""
# TODO: Normalize linguistic findings into unified schema
# TODO: Normalize traceability findings into unified schema
# TODO: Severity classification per §3.4 severity model
# TODO: Persist to issues table
