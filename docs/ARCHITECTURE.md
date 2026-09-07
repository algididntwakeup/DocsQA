# Architecture

Extraction creates canonical page/text/table evidence. Deterministic analyzers emit normalized findings with coordinates. Curation persists `included_in_report` and an optional note. `pypdf` annotates source PDF pages and `python-docx` builds review reports.

Future standards packs live outside Git in a licensed reference-library volume with manifests for edition, license, rules, chunks, and source pages. Raw standards PDFs are not ingested by v1.
