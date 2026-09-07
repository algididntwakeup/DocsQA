# Official Reference Standards Library

This directory stores authoritative, licensed source standard PDF documents used by DocsQA's reference-pack governance system.

## Policy & Licensing Rules

1. **Deterministic Verification Only**: Reference rules must only be derived from verifiable clauses, tables, and limits present in official standard editions.
2. **No Hallucination**: Do not invent clauses, page numbers, or numeric limits. If an official source PDF is missing, its reference pack status must remain `UNCONFIGURED` with 0 active rules.
3. **No Copyrighted Files in Git**: Official standards PDFs are copyrighted documents and **must never be committed to version control**. The local `.gitignore` prevents `*.pdf` files in this directory from being tracked by git.
4. **No External LLMs/APIs**: Document and standard evaluations are performed entirely locally and deterministically.

## Target Standard Documents

Place licensed PDF files corresponding to supported standards in this folder:

| Standard Code | Standard Title | Expected Filename | Active Edition |
| :--- | :--- | :--- | :--- |
| **ASME BPVC.VIII.1** | Rules for Construction of Pressure Vessels | `ASME_BPVC_VIII_1_2021.pdf` | 2021 |
| **API RP 580** | Risk-Based Inspection | `API_RP_580.pdf` | 3rd Ed. (2016) / 4th Ed. (2024) |
| **API 510** | Pressure Vessel Inspection Code: In-service Inspection, Rating, Repair, and Alteration | `API_510.pdf` | 11th Ed. (2022) |
| **API 579-1/ASME FFS-1** | Fitness-For-Service | `API_579_1.pdf` | 3rd Ed. (2021) |

## Pack Lifecycle

- **UNCONFIGURED**: Metadata and schema are defined, but the official source PDF has not been validated in `reference-library/`. No rules or benchmarks are active.
- **CONFIGURED**: Official source PDF is referenced, governed deterministic rules are authored with clause and page numbers, and all rules pass a comprehensive benchmark test suite (100% precision, 0% FPR).
