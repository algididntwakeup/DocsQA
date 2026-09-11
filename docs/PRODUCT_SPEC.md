# Product specification

DocsQA is a deterministic, on-premise engineering-document review tool. For each upload it produces a DOCX review draft and an annotated source PDF. A reviewer may include or exclude findings and add a note before export.

It checks technical terminology, spelling/grammar, units, table math, numerical claims, revision metadata, navigation drift, references, contradictions within the document, cross-page sentence continuity, narrative-heading style misclassifications, unintended whitespace / void pages, and document control integrity (running headers, footers, doc numbers, page numbers). It never approves engineering work, certifies safety, or validates external-standard compliance.

## Language and export preferences

- The frontend supports English (`en`) and Bahasa Indonesia (`id`).
- On first visit, the browser language is used: `id-*` selects Bahasa Indonesia; all other locales select English.
- An explicit frontend selection is stored in browser `localStorage` under `matqc-locale`. It is presentation state only and is not stored on users, projects, documents, or issues.
- The language toggle is available on login, the shared application shell, and the standalone review workspace.
- The DOCX export language is selected independently in the export modal. A report contains one language per file, not side-by-side translations.
- Report chrome and generated system prose are localized. Analyzer findings, evidence, filenames, identifiers, technical messages, source text, and reviewer notes remain verbatim for traceability.
- Annotated PDF export remains unchanged and retains original source annotations.
