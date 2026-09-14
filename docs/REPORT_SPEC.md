# Report specification

## Language contract

- The active formal DOCX renderer accepts `ReportLanguage`: `en` (English) or `id` (Bahasa Indonesia); omitted language defaults to English.
- `GET /documents/{document_id}/report?language=en|id` returns the same counts and a localized `summary_judgement`.
- `GET /documents/{document_id}/export?format=docx&language=en|id` localizes report labels and generated system prose.
- The annotated PDF export remains source-faithful; its language query value is ignored and persisted finding/evidence text remains unchanged.
- Source-derived content is never machine-translated: finding messages, codes, evidence, technical identifiers, source excerpts, and reviewer notes remain verbatim.

The report contains document identity, summary judgement, bottom line, scorecard, blockers, next-revision findings, language findings by page, optional demonstration rewrite, positive observations, and review limits. Each included finding states rule ID, severity, page, evidence, detected fact, recommendation, and reviewer note.

## Budinski scoring contract

- Appendix 12 checklist scores are integers from 1 through 5. A score of zero is never a valid evaluation result.
- Persisted legacy scorecards containing `score=0` are normalized to `score=null` and `status=NOT_APPLICABLE` during export validation.
- `ScoreItem` and `ScorecardEntry` use `score=null` for an item that is not applicable, rather than assigning a penalty score.
- Group and overall averages exclude `NOT_APPLICABLE` items. Evaluated averages are therefore between 1.00 and 5.00.
- SoR, Specification, and Procedure documents exclude laboratory-only checks such as experimental steps, repeatability detail, and discussion-specific items. The detailed appendix displays these items as `N/A`.
- The four baseline measures distinguish the purpose of the report from the objective of the work. A Scope section can satisfy this measure when it identifies the intended audience and required decision or action. Recommendations pass only when actions have a target date/deadline and a responsible party.

## Executive DOCX structure

The production DOCX export is executive-first and deterministic:

1. Document title, document ID, review date, reviewer/PIC, and verdict badge (`LAYAK TERBIT`, `PERLU PERBAIKAN (REWORK)`, or `DITOLAK`).
2. Executive summary with no more than five concrete recommended actions.
3. Four-pillar Budinski summary showing evaluated averages and status.
4. Consolidated critical findings with location/page range, issue type, source excerpt, and corrective action. Repeated `UNCONTROLLED_PAGE` and `CROSS_PAGE_BREAK` findings are summarized rather than printed as duplicate paragraphs.
5. Appendix A containing the detailed 41-item Appendix 12 checklist.

The report synthesizer uses persisted evidence excerpts for `Isi dokumen`/source text and generates separate corrective guidance. It must not repeat the finding boilerplate as the document excerpt.

Focused regression command:

```powershell
python -m pytest backend/tests/test_budinski_evaluator.py backend/tests/test_report.py backend/tests/test_review_export.py -q
```
