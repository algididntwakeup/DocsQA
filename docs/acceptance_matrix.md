# MVP Acceptance Matrix

**Status:** PROPOSED — awaiting product-owner approval

**Version:** 0.1

**Prepared:** 2026-09-04

This document makes the Phase 1 PRD measurable. Until its product decisions are
approved, agents may build contracts and test harnesses but must not claim the
M0 product gate is complete.

## 1. Proposed Product Boundaries

| Decision | Proposed Phase 1 value | Release behavior |
|---|---|---|
| Accepted inputs | Native-text PDF and DOCX | Other formats rejected with stable error code |
| Scanned/image-only input | Upload allowed; OCR best-effort behind feature flag | Clearly marked low confidence; excluded from F10/F11 release metrics |
| File size | 50 MiB per file | Stream rejected once limit is exceeded |
| Page count | 200 rendered pages per document | Extraction stops safely and reports limit error |
| Batch size | 20 files per upload action | Each file has an independent result |
| Canonical rendition | Original PDF; DOCX converted to canonical PDF by LibreOffice headless | All review pages and coordinates target canonical PDF |
| Flat tables | Supported | Merged, nested, and multi-page table inference is Phase 2 |
| Languages | English engineering documents | Other language content is accepted but linguistic stages report unsupported/low-confidence state |
| Export | Annotated PDF plus two-sheet XLSX issue log | CSV may be offered as a convenience, not a substitute for the XLSX audit log |
| DOCX tracked changes | Not a Phase 1 release requirement | Requires a separately validated implementation |
| Authentication | May be disabled only in explicit local single-user mode | RBAC is mandatory for shared/staging/production deployment |
| Roles | Inspector, QA Engineer, Lead Reviewer, Admin | Server-side authorization; UI hiding alone is insufficient |
| Retention | 90 days after last document activity by default | Admin-configurable; audit retention must follow organization policy |
| Deletion | Soft-delete immediately; purge file/artifacts after retention window | Audit events remain append-only for the configured audit-retention period |
| Duplicate upload | Same hash allowed as a new version; duplicate active scan is deduplicated | API returns/links the active scan deterministically |
| Time zone | Store UTC; display user locale | API timestamps are ISO-8601 UTC |

## 2. Status and Failure Acceptance

Allowed document processing states:

```text
QUEUED -> PROCESSING -> COMPLETED
                     -> COMPLETED_WITH_WARNINGS
                     -> FAILED
```

- `COMPLETED`: all required enabled stages succeeded.
- `COMPLETED_WITH_WARNINGS`: extraction succeeded and usable results exist, but
  one or more non-foundational stages failed or returned degraded confidence.
- `FAILED`: upload persistence or canonical extraction failed, so meaningful
  review cannot continue.
- Every retry creates new stage-run records; it does not overwrite prior audit
  evidence.
- Stage failures expose stable error codes and sanitized messages, never raw
  stack traces or document contents.

## 3. Ground-Truth Corpus

Create a versioned manifest at `backend/tests/fixtures/manifest.json`. Every
fixture records: fixture ID, SHA-256, format, page count, eligibility by metric,
expected issues/evidence, source/license, and reviewer approval.

Minimum pre-release corpus:

| Feature | Minimum eligible cases | Required distribution |
|---|---:|---|
| Spelling/domain terms | 1,000 labeled tokens | At least 500 valid domain terms and 100 true misspellings |
| Table math | 200 labeled total assertions across at least 30 documents | Correct totals, mismatches, rounding boundary, units, thousands/decimal separators, malformed rows |
| Reference drift | 150 labeled ToC/LoF/LoT entries across at least 20 documents | Correct, +/− drift, roman front matter, missing target, duplicate caption |
| Revision sync | 100 eligible documents | All-equal plus each pairwise/three-way mismatch and missing source |
| Standards traceability | 200 labeled body citations across at least 25 documents | Present, missing bibliography, year match/mismatch, ambiguous code |
| Performance | 30 representative 20-page native-text PDFs | Small/large tables and typical linguistic density |
| Reviewer timing | At least 10 reviewers × 5 paired documents | Counter-balanced manual vs assisted review |

Synthetic fixtures are allowed for edge cases, but at least 30% of metric cases
must be de-identified representative engineering documents. Tuning and final
evaluation sets must be document-disjoint.

## 4. Metric Definitions and Gates

| PRD metric | Exact calculation | Gate |
|---|---|---|
| Domain-term false-positive rate | valid domain tokens incorrectly flagged / all labeled valid domain tokens | `< 5%` on held-out set |
| Table math correctness | correctly classified eligible total assertions / all eligible labeled total assertions | `>= 98%`; also report mismatch precision and recall |
| Reference drift recall | true drift findings / all labeled drift cases | `>= 95%`; precision must be `>= 90%` |
| Revision mismatch detection | correctly classified eligible documents / all eligible documents | `100%`; missing-source cases reported separately |
| Standard traceability coverage | correctly detected resolvable body citations / all labeled resolvable body citations | `>= 95%`; report missing-reference and edition-year metrics separately |
| Processing time | worker start through terminal processing state; excludes upload and queue delay | mean `< 20s`, p95 `< 30s` for the performance corpus |
| Reviewer time saved | `(median manual time - median assisted time) / median manual time` on paired tasks | `>= 50%`, with error counts no worse than manual baseline |

For every reported result, store application commit, extractor/rule versions,
corpus version, runtime versions, machine profile, warm/cold state, raw counts,
and excluded cases. A percentage without numerator and denominator does not pass.

## 5. Functional Release Scenarios

| ID | Scenario | Pass condition |
|---|---|---|
| A-01 | Upload valid PDF | `201`, immutable hash/storage record, queued scan |
| A-02 | Upload valid DOCX | Canonical PDF generated; page/anchor artifact persisted |
| A-03 | Invalid or disguised file | Rejected without persistent partial file or stack trace |
| A-04 | Partial analyzer failure | Successful findings remain; status is `COMPLETED_WITH_WARNINGS` |
| A-05 | Table mismatch | Both source cells and stated-total cell are addressable; Decimal evidence retained |
| A-06 | Reference drift | ToC/list entry and actual target are independently navigable |
| A-07 | Revision mismatch | Filename, cover, and latest revision-row evidence identify disagreements |
| A-08 | Missing/misdated standard | Normalized code and body/reference evidence are shown |
| A-09 | Review decision | Authorized actor can decide once; conflicting update returns version conflict |
| A-10 | Traceability bulk accept | Rejected by API and unavailable in UI |
| A-11 | Approval mutation | Prior disposition/audit event remains immutable; new action appends an event |
| A-12 | Export | PDF annotations align with canonical pages; XLSX has Language and Traceability sheets |
| A-13 | Role boundary | Each role's allowed and denied operations are API-tested |
| A-14 | Retention purge | Eligible blobs/artifacts purge; configured audit evidence remains |
| A-15 | Full flow | Upload -> scan -> review -> disposition -> export passes in Playwright |

## 6. Product-Owner Approval Checklist

Approve or amend each item before changing this document to `APPROVED`:

- [ ] 50 MiB file limit
- [ ] 200-page document limit
- [ ] 20-file batch limit
- [ ] English-only linguistic quality target for Phase 1
- [ ] 90-day default document retention
- [ ] Annotated PDF + two-sheet XLSX as required exports
- [ ] DOCX tracked changes deferred from Phase 1
- [ ] RBAC required before any shared deployment
- [ ] OCR excluded from F10/F11 metric claims
- [ ] Minimum corpus sizes and measurement formulas
- [ ] Representative documents can be legally de-identified and used for QA

Approval record:

```text
Owner:
Date:
Decision: APPROVED / APPROVED WITH CHANGES / REJECTED
Changes:
```
