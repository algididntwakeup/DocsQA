# Report specification

## Language contract

- The active formal DOCX renderer accepts `ReportLanguage`: `en` (English) or `id` (Bahasa Indonesia); omitted language defaults to English.
- `GET /documents/{document_id}/report?language=en|id` returns the same counts and a localized `summary_judgement`.
- `GET /documents/{document_id}/export?format=docx&language=en|id` localizes report labels and generated system prose.
- The annotated PDF export remains source-faithful; its language query value is ignored and persisted finding/evidence text remains unchanged.
- Source-derived content is never machine-translated: finding messages, codes, evidence, technical identifiers, source excerpts, and reviewer notes remain verbatim.

The report contains document identity, summary judgement, bottom line, scorecard, blockers, next-revision findings, language findings by page, optional demonstration rewrite, positive observations, and review limits. Each included finding states rule ID, severity, page, evidence, detected fact, recommendation, and reviewer note.
