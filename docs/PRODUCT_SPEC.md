# Product specification

PRISM is a deterministic, on-premise engineering-document review tool. For each upload it produces a DOCX review draft and an annotated source PDF. A reviewer may include or exclude findings and add a note before export.

It checks technical terminology, spelling/grammar, units, table math, numerical claims, revision metadata, navigation drift, references, contradictions within the document, cross-page sentence continuity, narrative-heading style misclassifications, unintended whitespace / void pages, and document control integrity (running headers, footers, doc numbers, page numbers). It never approves engineering work, certifies safety, or validates external-standard compliance.

## Sign-in and workspace access

- The frontend login page has one sign-in action: BIMA SSO. No email/password login or self-registration form is available.
- BIMA supplies authenticated identity and roles; PRISM issues its own session after validating the BIMA SSO callback.
- Lead engineers and superusers synchronize BIMA projects and user directory data into PRISM workspaces.
- BIMA project membership grants read access to that project and its documents only. Membership does not grant write, assignment, review, or issue-curation authority.

## Language and export preferences

- The frontend supports English (`en`) and Bahasa Indonesia (`id`).
- On first visit, the browser language is used: `id-*` selects Bahasa Indonesia; all other locales select English.
- An explicit frontend selection is stored in browser `localStorage` under `matqc-locale`. It is presentation state only and is not stored on users, projects, documents, or issues.
- The language toggle is available on login, the shared application shell, and the standalone review workspace.
- The DOCX export language is selected independently in the export modal. A report contains one language per file, not side-by-side translations.
- Report chrome, generated system prose, and finding-type labels are localized. Canonical analyzer type keys are rendered as readable labels in executive DOCX and compiled PDF reports. Analyzer messages, evidence, filenames, technical identifiers, source text, and reviewer notes remain verbatim for traceability.
- Annotated PDF export remains source-faithful: source page content and stored finding/evidence annotations are preserved.

## Report header and letterhead

- Lead engineers and superusers can configure the default report header from a project's detail page. The settings are stored with the project and used for documents in that project.
- The shared header editor is also available in the export dialog. Changes made there apply only to that export; they do not update the saved project default.
- The header supports the Reksolindo and client logos, a centered title, an optional divider, and four placements: company left/client right, client left/company right, both logos left, or both logos right.
- PDF and DOCX review reports use the same repeating page header. The annotated source PDF is unchanged.
- Header logos are uploaded as image data and persisted in the project header configuration. The company logo defaults to the bundled Reksolindo asset when no replacement is provided.
