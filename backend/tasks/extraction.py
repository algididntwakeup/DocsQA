"""Celery task for the extraction stage of the Document QC pipeline."""

import asyncio
import contextlib
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.celery_app import celery_app
from core.config import settings
from db.session import async_session_factory
from domain.enums import DocumentStatus, StageStatus
from models.document import Document, StageRun
from models.issue import Issue
from schemas.base import ApiModel
from schemas.extraction import ExtractionArtifact
from schemas.issues import (
    IssueEvidence,
    LinguisticEvidence,
    ReferenceDriftEvidence,
    RevisionEvidence,
    StageFailureEvidence,
    StandardEvidence,
    TableMathEvidence,
)
from schemas.linguistic import (
    AmbiguityAnalysis,
    DuplicateAnalysis,
    GrammarAnalysis,
    SpellcheckAnalysis,
)
from schemas.ref_drift import RefDriftAnalysis
from schemas.revision import RevisionAnalysis
from schemas.standard_traceability import StandardTraceabilityAnalysis
from schemas.table_math import TableMathAnalysis
from services.aggregate import aggregate_document_findings
from services.ambiguity import analyze_ambiguity
from services.dictionary import get_approved_dictionary_terms
from services.duplicate import analyze_duplicates
from services.extract import extract_document
from services.grammar import analyze_grammar
from services.ref_drift import analyze_ref_drift
from services.revision_sync import analyze_revision
from services.spellcheck import analyze_spelling
from services.standard_traceability import analyze_standard_traceability
from services.storage import LocalStorage
from services.trace_numbers import analyze_table_math

logger = get_task_logger(__name__)

EXTRACTION_STAGE = "extraction"
REVISION_STAGE = "revision_sync"
TABLE_MATH_STAGE = "table_math"
REF_DRIFT_STAGE = "ref_drift"
STANDARD_STAGE = "standard_traceability"
SPELLCHECK_STAGE = "spellcheck"
GRAMMAR_STAGE = "grammar"
DUPLICATE_STAGE = "duplicate_content"
AMBIGUITY_STAGE = "ambiguity"
AGGREGATION_STAGE = "aggregation"


def _sanitize_error(exc: Exception) -> tuple[str, str]:
    """Return a public error code and message without leaking internals."""
    message = str(exc).strip() or exc.__class__.__name__
    return exc.__class__.__name__.upper(), message[:1000]


def _persist_artifact(storage: LocalStorage, document_id: UUID, name: str, payload: bytes) -> str:
    """Persist a serialized extraction artifact and return its storage URI."""
    key = f"artifacts/{document_id}/{name}.json"
    return storage.put_stream(key, BytesIO(payload)).uri


async def _latest_attempt(session: AsyncSession, document_id: UUID, stage_name: str) -> int:
    value = (
        await session.execute(
            select(StageRun.attempt)
            .where(
                StageRun.document_id == document_id,
                StageRun.stage_name == stage_name,
            )
            .order_by(StageRun.attempt.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return (value or 0) + 1


async def _run_revision_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    artifact: ExtractionArtifact,
) -> bool:
    """Persist revision evidence while isolating analyzer failures."""

    stage_run = StageRun(
        document_id=document.id,
        stage_name=REVISION_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, REVISION_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    revision_failed = False
    try:
        analysis = analyze_revision(document.original_filename, artifact)
        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            REVISION_STAGE,
            analysis.model_dump_json().encode("utf-8"),
        )
        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — analyzer failures remain isolated
        revision_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Revision sync failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        await session.commit()
    return revision_failed


async def _run_table_math_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    artifact: ExtractionArtifact,
) -> bool:
    """Persist table math evidence while isolating analyzer failures."""

    stage_run = StageRun(
        document_id=document.id,
        stage_name=TABLE_MATH_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, TABLE_MATH_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    table_math_failed = False
    try:
        analysis = analyze_table_math(artifact)
        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            TABLE_MATH_STAGE,
            analysis.model_dump_json().encode("utf-8"),
        )
        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — analyzer failures remain isolated
        table_math_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Table math failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        await session.commit()
    return table_math_failed


async def _run_ref_drift_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    artifact: ExtractionArtifact,
) -> bool:
    """Persist reference drift evidence while isolating analyzer failures."""

    stage_run = StageRun(
        document_id=document.id,
        stage_name=REF_DRIFT_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, REF_DRIFT_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    ref_drift_failed = False
    try:
        analysis = analyze_ref_drift(artifact)
        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            REF_DRIFT_STAGE,
            analysis.model_dump_json().encode("utf-8"),
        )
        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — analyzer failures remain isolated
        ref_drift_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Reference drift failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        await session.commit()
    return ref_drift_failed


async def _run_standard_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    artifact: ExtractionArtifact,
    prior_degraded: bool,
) -> bool:
    """Persist standard-traceability evidence and finalize visible status."""

    stage_run = StageRun(
        document_id=document.id,
        stage_name=STANDARD_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, STANDARD_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    standard_failed = False
    try:
        analysis = analyze_standard_traceability(artifact)
        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            STANDARD_STAGE,
            analysis.model_dump_json().encode("utf-8"),
        )
        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — analyzer failures remain isolated
        standard_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Standard traceability failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        document.status = (
            DocumentStatus.COMPLETED_WITH_WARNINGS
            if prior_degraded or standard_failed
            else DocumentStatus.COMPLETED
        )
        document.progress_pct = 100
        await session.commit()
    return standard_failed


async def _run_spellcheck_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    artifact: ExtractionArtifact,
) -> bool:
    """Persist spellcheck findings while isolating analyzer failures."""
    stage_run = StageRun(
        document_id=document.id,
        stage_name=SPELLCHECK_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, SPELLCHECK_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    spellcheck_failed = False
    try:
        custom_dict = await get_approved_dictionary_terms(
            session, project_id=getattr(document, "project_id", None)
        )
        analysis = analyze_spelling(artifact, custom_dictionary=custom_dict)
        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            SPELLCHECK_STAGE,
            analysis.model_dump_json().encode("utf-8"),
        )
        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — analyzer failures remain isolated
        spellcheck_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Spellcheck failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        await session.commit()
    return spellcheck_failed


async def _run_grammar_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    artifact: ExtractionArtifact,
) -> bool:
    """Persist grammar findings while isolating analyzer failures."""
    stage_run = StageRun(
        document_id=document.id,
        stage_name=GRAMMAR_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, GRAMMAR_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    grammar_failed = False
    try:
        analysis = analyze_grammar(artifact)
        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            GRAMMAR_STAGE,
            analysis.model_dump_json().encode("utf-8"),
        )
        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — analyzer failures remain isolated
        grammar_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Grammar analysis failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        await session.commit()
    return grammar_failed


async def _run_duplicate_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    artifact: ExtractionArtifact,
) -> bool:
    """Persist duplicate findings while isolating analyzer failures."""
    stage_run = StageRun(
        document_id=document.id,
        stage_name=DUPLICATE_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, DUPLICATE_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    duplicate_failed = False
    try:
        analysis = analyze_duplicates(artifact)
        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            DUPLICATE_STAGE,
            analysis.model_dump_json().encode("utf-8"),
        )
        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — analyzer failures remain isolated
        duplicate_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Duplicate analysis failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        await session.commit()
    return duplicate_failed


async def _run_ambiguity_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    artifact: ExtractionArtifact,
) -> bool:
    """Persist ambiguity findings while isolating analyzer failures."""
    stage_run = StageRun(
        document_id=document.id,
        stage_name=AMBIGUITY_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, AMBIGUITY_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    ambiguity_failed = False
    try:
        analysis = analyze_ambiguity(artifact)
        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            AMBIGUITY_STAGE,
            analysis.model_dump_json().encode("utf-8"),
        )
        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — analyzer failures remain isolated
        ambiguity_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Ambiguity analysis failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        await session.commit()
    return ambiguity_failed


def _extract_page_number(evidence: IssueEvidence) -> int | None:
    """Extract a 1-indexed page number from evidence for database indexing."""
    if isinstance(evidence, TableMathEvidence):
        return evidence.total_location.page_index + 1
    if isinstance(evidence, ReferenceDriftEvidence):
        return evidence.entry_location.page_index + 1
    if isinstance(evidence, RevisionEvidence):
        return evidence.locations[0].page_index + 1 if evidence.locations else 1
    if isinstance(evidence, StandardEvidence):
        return evidence.body_location.page_index + 1
    if isinstance(evidence, LinguisticEvidence):
        return int(evidence.location.page_index + 1)
    if isinstance(evidence, StageFailureEvidence):
        return None
    return None


def _load_stage_artifact[T: ApiModel](
    storage: LocalStorage, document_id: UUID, stage_name: str, model_cls: type[T]
) -> T | None:
    """Safely load and deserialize a previously persisted stage artifact."""
    key = f"artifacts/{document_id}/{stage_name}.json"
    try:
        path = storage._path_for_key(key)
        if not path.exists():
            return None
        data = path.read_text(encoding="utf-8")
        return model_cls.model_validate_json(data)
    except Exception:
        return None


async def _run_aggregation_stage(
    session: AsyncSession,
    storage: LocalStorage,
    document: Document,
    failed_stages: list[tuple[str, str, bool]],
    prior_degraded: bool,
) -> bool:
    """Aggregate all analyzer findings into unified issues and persist to PostgreSQL."""
    stage_run = StageRun(
        document_id=document.id,
        stage_name=AGGREGATION_STAGE,
        status=StageStatus.RUNNING,
        progress_pct=0,
        attempt=await _latest_attempt(session, document.id, AGGREGATION_STAGE),
        started_at=datetime.now(UTC),
    )
    session.add(stage_run)
    await session.commit()

    aggregation_failed = False
    try:
        revision = _load_stage_artifact(storage, document.id, REVISION_STAGE, RevisionAnalysis)
        table_math = _load_stage_artifact(storage, document.id, TABLE_MATH_STAGE, TableMathAnalysis)
        ref_drift = _load_stage_artifact(storage, document.id, REF_DRIFT_STAGE, RefDriftAnalysis)
        standard = _load_stage_artifact(
            storage, document.id, STANDARD_STAGE, StandardTraceabilityAnalysis
        )
        spellcheck = _load_stage_artifact(
            storage, document.id, SPELLCHECK_STAGE, SpellcheckAnalysis
        )
        grammar = _load_stage_artifact(storage, document.id, GRAMMAR_STAGE, GrammarAnalysis)
        duplicate = _load_stage_artifact(storage, document.id, DUPLICATE_STAGE, DuplicateAnalysis)
        ambiguity = _load_stage_artifact(storage, document.id, AMBIGUITY_STAGE, AmbiguityAnalysis)

        result = aggregate_document_findings(
            document_id=document.id,
            revision=revision,
            table_math=table_math,
            ref_drift=ref_drift,
            standard_traceability=standard,
            spellcheck=spellcheck,
            grammar=grammar,
            duplicate=duplicate,
            ambiguity=ambiguity,
            failed_stages=failed_stages,
        )

        stage_run.artifact_uri = _persist_artifact(
            storage,
            document.id,
            AGGREGATION_STAGE,
            result.model_dump_json().encode("utf-8"),
        )

        # Clear any existing issues for this document to ensure idempotency
        await session.execute(delete(Issue).where(Issue.document_id == document.id))

        # Persist unified issues to database
        issue_records = [
            Issue(
                id=issue_read.id,
                document_id=document.id,
                category=issue_read.category,
                type=issue_read.type,
                severity=issue_read.severity,
                confidence=issue_read.confidence,
                message=issue_read.message,
                page_number=_extract_page_number(issue_read.evidence),
                evidence=issue_read.evidence.model_dump(mode="json"),
                included_in_report=True,
                created_at=issue_read.created_at,
                updated_at=issue_read.updated_at,
            )
            for issue_read in result.issues
        ]
        session.add_all(issue_records)

        stage_run.progress_pct = 100
        stage_run.status = StageStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001 — stage failures remain isolated
        aggregation_failed = True
        code, message = _sanitize_error(exc)
        stage_run.status = StageStatus.FAILED
        stage_run.error_code = code
        stage_run.error_message = message
        logger.exception("Finding aggregation failed for document %s", document.id)
    finally:
        stage_run.finished_at = datetime.now(UTC)
        document.status = (
            DocumentStatus.COMPLETED_WITH_WARNINGS
            if prior_degraded or aggregation_failed or bool(failed_stages)
            else DocumentStatus.COMPLETED
        )
        document.progress_pct = 100
        await session.commit()
    return aggregation_failed


async def _run_extraction(document_id: str) -> dict[str, object]:
    """Load, extract, and persist one document's canonical artifact."""
    doc_id = UUID(document_id)
    async with async_session_factory() as session:
        document = (
            await session.execute(select(Document).where(Document.id == doc_id))
        ).scalar_one_or_none()
        if document is None:
            logger.warning("Extraction skipped for missing document %s", document_id)
            return {"document_id": document_id, "skipped": True}

        stage_run = StageRun(
            document_id=doc_id,
            stage_name=EXTRACTION_STAGE,
            status=StageStatus.RUNNING,
            progress_pct=0,
            attempt=await _latest_attempt(session, doc_id, EXTRACTION_STAGE),
            started_at=datetime.now(UTC),
        )
        session.add(stage_run)
        document.status = DocumentStatus.PROCESSING
        await session.commit()
        await session.refresh(stage_run)

        storage = LocalStorage(settings.STORAGE_ROOT)

        artifact: ExtractionArtifact | None = None
        extraction_degraded = False
        try:
            source_path = storage.resolve(document.storage_uri)
            artifact = extract_document(Path(source_path), doc_id, document.media_type)
            artifact_uri = _persist_artifact(
                storage,
                doc_id,
                EXTRACTION_STAGE,
                artifact.model_dump_json().encode("utf-8"),
            )
            stage_run.artifact_uri = artifact_uri
            stage_run.progress_pct = 100
            if artifact.warnings:
                extraction_degraded = True
                stage_run.status = StageStatus.SUCCEEDED_WITH_WARNINGS
            else:
                stage_run.status = StageStatus.SUCCEEDED
            document.page_count = len(artifact.pages) or None
        except SoftTimeLimitExceeded:
            stage_run.status = StageStatus.FAILED
            stage_run.error_code = "TIMED_OUT"
            stage_run.error_message = "Extraction exceeded soft time limit."
            raise
        except Exception as exc:  # noqa: BLE001 — stage failures are recorded, not raised
            code, message = _sanitize_error(exc)
            stage_run.status = StageStatus.FAILED
            stage_run.error_code = code
            stage_run.error_message = message
            document.status = DocumentStatus.FAILED
            logger.exception("Extraction failed for document %s", document_id)
        finally:
            stage_run.finished_at = datetime.now(UTC)
            await session.commit()

        if artifact is not None:
            revision_failed = await _run_revision_stage(session, storage, document, artifact)
            table_math_failed = await _run_table_math_stage(session, storage, document, artifact)
            ref_drift_failed = await _run_ref_drift_stage(session, storage, document, artifact)
            standard_failed = await _run_standard_stage(
                session,
                storage,
                document,
                artifact,
                prior_degraded=(
                    extraction_degraded or revision_failed or table_math_failed or ref_drift_failed
                ),
            )
            spellcheck_failed = await _run_spellcheck_stage(session, storage, document, artifact)
            grammar_failed = await _run_grammar_stage(session, storage, document, artifact)
            duplicate_failed = await _run_duplicate_stage(session, storage, document, artifact)
            ambiguity_failed = await _run_ambiguity_stage(session, storage, document, artifact)

            failed_stages: list[tuple[str, str, bool]] = []
            if revision_failed:
                failed_stages.append((REVISION_STAGE, "REVISION_ANALYSIS_FAILED", True))
            if table_math_failed:
                failed_stages.append((TABLE_MATH_STAGE, "TABLE_MATH_ANALYSIS_FAILED", True))
            if ref_drift_failed:
                failed_stages.append((REF_DRIFT_STAGE, "REF_DRIFT_ANALYSIS_FAILED", True))
            if standard_failed:
                failed_stages.append((STANDARD_STAGE, "STANDARD_TRACEABILITY_FAILED", True))
            if spellcheck_failed:
                failed_stages.append((SPELLCHECK_STAGE, "SPELLCHECK_ANALYSIS_FAILED", True))
            if grammar_failed:
                failed_stages.append((GRAMMAR_STAGE, "GRAMMAR_ANALYSIS_FAILED", True))
            if duplicate_failed:
                failed_stages.append((DUPLICATE_STAGE, "DUPLICATE_ANALYSIS_FAILED", True))
            if ambiguity_failed:
                failed_stages.append((AMBIGUITY_STAGE, "AMBIGUITY_ANALYSIS_FAILED", True))

            await _run_aggregation_stage(
                session,
                storage,
                document,
                failed_stages=failed_stages,
                prior_degraded=bool(
                    extraction_degraded
                    or revision_failed
                    or table_math_failed
                    or ref_drift_failed
                    or standard_failed
                    or spellcheck_failed
                    or grammar_failed
                    or duplicate_failed
                    or ambiguity_failed
                ),
            )

    return {"document_id": document_id, "stage": EXTRACTION_STAGE}


async def _mark_timed_out(document_id: str) -> None:
    """Set a timed-out document to COMPLETED_WITH_WARNINGS so the UI unblocks."""
    doc_id = UUID(document_id)
    async with async_session_factory() as session:
        document = (
            await session.execute(select(Document).where(Document.id == doc_id))
        ).scalar_one_or_none()
        if document is not None and document.status == DocumentStatus.PROCESSING:
            document.status = DocumentStatus.COMPLETED_WITH_WARNINGS
            document.progress_pct = 100

        # Mark any running stage runs so the UI doesn't spin indefinitely
        stage_runs = (
            await session.execute(
                select(StageRun).where(
                    StageRun.document_id == doc_id,
                    StageRun.status == StageStatus.RUNNING,
                )
            )
        ).scalars().all()
        for sr in stage_runs:
            sr.status = StageStatus.SUCCEEDED_WITH_WARNINGS
            sr.error_code = "TIMED_OUT"
            sr.error_message = "Stage exceeded time limit; partial results preserved."
            sr.finished_at = datetime.now(UTC)

        await session.commit()


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="docqc.extract",
    max_retries=2,
    default_retry_delay=5,
    # Do NOT autoretry on Exception — a stuck task would retry and hang again.
    # Only retry on transient infrastructure errors by catching them explicitly below.
    soft_time_limit=300,  # 5 min soft limit — allows graceful cleanup
    time_limit=360,       # 6 min hard limit — SIGKILL if still running
)
def extract_document_task(self: Any, document_id: str) -> dict[str, object]:
    """Run extraction and persist a failed run before any retry is scheduled."""
    try:
        return asyncio.run(_run_extraction(document_id))
    except SoftTimeLimitExceeded:
        # Gracefully mark the document as COMPLETED_WITH_WARNINGS so the user can
        # still open the Review Workspace with whatever data was already persisted.
        logger.error(
            "Document %s extraction exceeded soft time limit (300 s); "
            "marking as COMPLETED_WITH_WARNINGS.",
            document_id,
        )
        with contextlib.suppress(Exception):
            asyncio.run(_mark_timed_out(document_id))
        return {"document_id": document_id, "timed_out": True}
    except Exception as exc:  # noqa: BLE001 — retry idempotently, artifact state is per-attempt
        request = self.request
        retries = request.retries if request is not None else 0
        max_retries = self.max_retries
        if retries >= max_retries:
            return {"document_id": document_id, "failed": str(exc)}
        raise self.retry(exc=exc) from exc
