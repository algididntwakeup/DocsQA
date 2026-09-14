# Report specification

## Language contract

- The active formal DOCX and PDF renderers accept `ReportLanguage`: `en` (English) or `id` (Bahasa Indonesia); omitted language defaults to English (`en`).
- `GET /documents/{document_id}/report?language=en|id` returns counts and a localized `summary_judgement`.
- `GET /documents/{document_id}/export?format=docx&language=en|id` localizes report labels, baseline measures, scorecard categories, actions, recommendations, and system prose in the DOCX deliverable.
- `GET /documents/{document_id}/export?format=pdf&language=en|id` converts the localized review DOCX to a production-ready PDF via Headless LibreOffice (`soffice`), ensuring exact visual formatting and tables.
- Strict language isolation ("Anti-Bahasa Belang"): Selecting English enforces 0 Indonesian words in generated prose, titles, and checklist items. Selecting Indonesian enforces 0 English boilerplate phrases.
- The 41 Budinski checklist items in Appendix A are localized deterministically via `BUDINSKI_41_ITEMS` dictionary in `backend/services/report_locale.py`.
- The annotated PDF export (`format=annotated_pdf`) remains source-faithful; its language query value is ignored and persisted finding/evidence text remains unchanged.
- Source-derived content is never machine-translated: finding messages, codes, evidence, technical identifiers, source excerpts, and reviewer notes remain verbatim.

The report contains document identity, summary judgement, bottom line, scorecard, blockers, next-revision findings, language findings by page, optional demonstration rewrite, positive observations, and review limits. Each included finding states rule ID, severity, page, evidence, detected fact, recommendation, and reviewer note.

## Budinski scoring contract

- Appendix 12 checklist scores are integers from 1 through 5. A score of zero is never a valid evaluation result.
- Persisted legacy scorecards containing `score=0` are normalized to `score=null` and `status=NOT_APPLICABLE` during export validation.
- `ScoreItem` and `ScorecardEntry` use `score=null` for an item that is not applicable, rather than assigning a penalty score.
- Group and overall averages exclude `NOT_APPLICABLE` items. Evaluated averages are therefore between 1.00 and 5.00.
- SoR, Specification, and Procedure documents exclude laboratory-only checks such as experimental steps, repeatability detail, and discussion-specific items. The detailed appendix displays these items as `N/A`.
- The four baseline measures distinguish the purpose of the report from the objective of the work. A Scope section can satisfy this measure when it identifies the intended audience and required decision or action. Recommendations pass only when actions have a target date/deadline and a responsible party.

## Executive Report Deliverable Structure (DOCX & PDF)

The production export (available as PDF or DOCX) is executive-first and 100% deterministic:

1. Document title, document ID, review date, reviewer/PIC, and localized verdict badge (`LAYAK TERBIT` / `PASSED`, `PERLU PERBAIKAN (REWORK)` / `REWORK REQUIRED`, or `DITOLAK` / `REJECTED`).
2. Executive summary with no more than five concrete recommended actions.
3. Four-pillar Budinski summary showing evaluated averages and status.
4. Consolidated critical findings with location/page range, issue type, source excerpt, and corrective action. Repeated `UNCONTROLLED_PAGE` and `CROSS_PAGE_BREAK` findings are summarized rather than printed as duplicate paragraphs.
5. Next revision recommendations and language/drafting mechanics findings.
6. Optional demonstration revision / rewrite.
7. Issue category group summary.
8. Appendix A containing the detailed 41-item Budinski compliance checklist (fully translated into the target language).
9. Positive observations / What this document does well.
10. Limits of review and engineering scope.

The report synthesizer uses persisted evidence excerpts for source text and generates separate corrective guidance. It must not repeat the finding boilerplate as the document excerpt.

Focused regression command:

```powershell
python -m pytest backend/tests/test_budinski_evaluator.py backend/tests/test_report.py backend/tests/test_review_export.py -q
```

