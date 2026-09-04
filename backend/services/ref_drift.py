"""
Reference Drift Detection Service (F11)
==========================================
Parses ToC, List of Figures, List of Tables into structured entries.
Independently determines actual page locations via heading/caption detection.
Resolves front-matter vs body page-numbering offsets, then diffs.

Traceability pipeline — Stage 7.
Outputs: REF_DRIFT (with referenced_page, actual_page, delta)
"""
# TODO: ToC / LoF / LoT structured parse
# TODO: Heading/caption detection via font-size hierarchy (PDF) or style names (DOCX)
# TODO: Roman/Arabic page-numbering offset resolution
# TODO: Referenced vs actual page diff with delta calculation
