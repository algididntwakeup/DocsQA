import asyncio
import contextlib
import json
import shutil
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.dependencies import (
    get_accessible_document,
    get_current_user,
    get_storage,
    get_upload_service,
    require_lead,
)
from db.session import async_session_factory, get_session
from domain.enums import (
    DocumentStatus,
    DocumentWorkflowStatus,
    IssueCategory,
    PipelineStage,
    Severity,
    StageStatus,
    UserRole,
)
from models.document import Document, StageRun
from models.issue import Issue
from models.user import User
from schemas.common import PageInfo, ProblemDetail
from schemas.documents import (
    DocumentAssignment,
    DocumentListResponse,
    DocumentRead,
    DocumentStatusResponse,
    DocumentUploadResponse,
    DocumentWorkflowUpdate,
    ReviewReportPreview,
    StageRunRead,
    TraceabilitySummaryResponse,
)
from schemas.issues import IssueListResponse, IssueRead
from services.export import (
    assessment_from_document_findings,
    export_annotated_pdf,
    generate_ale_review_docx,
)
from services.pipeline import enqueue_extraction
from services.storage.local import LocalStorage
from services.uploads import UploadService

router = APIRouter(prefix="/documents", tags=["documents"])

WIP_ERROR = (
    "Kamu masih memiliki dokumen aktif yang sedang direview. "
    "Selesaikan review (Mark Reviewed) terlebih dahulu."
)


async def check_engineer_wip_available(
    session: AsyncSession, engineer_id: UUID
) -> tuple[bool, Document | None]:
    """Return whether an engineer has a free single-document WIP slot."""
    active_document = (
        await session.execute(
            select(Document)
            .where(
                Document.assigned_to_id == engineer_id,
                Document.workflow_status == DocumentWorkflowStatus.ANALYZING,
            )
            .order_by(Document.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return active_document is None, active_document


def _document_read(document: Document) -> DocumentRead:
    """Serialize a document with assignment and owner display metadata."""
    return DocumentRead.model_validate(document).model_copy(
        update={
            "owner_name": document.owner.full_name if document.owner else None,
            "assigned_to_name": document.assigned_to.full_name if document.assigned_to else None,
            "assigned_to_email": document.assigned_to.email if document.assigned_to else None,
        }
    )


async def _load_document_for_assignment(session: AsyncSession, document_id: UUID) -> Document:
    document = (
        await session.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(joinedload(Document.owner), joinedload(Document.assigned_to))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


@router.post("/{document_id}/claim", response_model=DocumentRead)
async def claim_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentRead:
    """Claim an unassigned document when the engineer has no active WIP."""
    if current_user.role != UserRole.ENGINEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Engineer access required."
        )
    await session.execute(select(User).where(User.id == current_user.id).with_for_update())
    document = await _load_document_for_assignment(session, document_id)
    if document.assigned_to_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Document is already assigned."
        )
    available, _ = await check_engineer_wip_available(session, current_user.id)
    if not available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=WIP_ERROR)
    document.assigned_to_id = current_user.id
    document.owner_id = current_user.id
    document.assigned_to = current_user
    document.owner = current_user
    await session.commit()
    await session.refresh(document)
    return _document_read(document)


@router.post("/{document_id}/assign", response_model=DocumentRead)
async def assign_document(
    document_id: UUID,
    payload: DocumentAssignment,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_lead)],
) -> DocumentRead:
    """Assign a document to an engineer, optionally overriding the WIP limit."""
    document = await _load_document_for_assignment(session, document_id)
    engineer = (
        await session.execute(
            select(User)
            .where(
                User.id == payload.engineer_id,
                User.is_active.is_(True),
                User.role == UserRole.ENGINEER,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if engineer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Engineer not found or inactive."
        )
    if not payload.override_wip:
        available, active_document = await check_engineer_wip_available(session, engineer.id)
        if not available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Engineer already has an active document.",
                    "active_document": {
                        "id": str(active_document.id),
                        "filename": active_document.original_filename,
                        "workflow_status": active_document.workflow_status.value,
                    },
                },
            )
    document.assigned_to_id = engineer.id
    document.owner_id = engineer.id
    document.assigned_to = engineer
    document.owner = engineer
    await session.commit()
    await session.refresh(document)
    return _document_read(document)


NOT_READY: dict[int | str, dict[str, Any]] = {
    501: {"model": ProblemDetail, "description": "Feature not implemented"}
}


@router.post("/{document_id}/mark-reviewed", response_model=DocumentRead)
async def mark_document_reviewed(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> DocumentRead:
    """Mark an owned document as reviewed by its engineer owner."""
    if document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Document owner access required."
        )
    document.workflow_status = DocumentWorkflowStatus.REVIEWED_BY_ENGINEER
    document.reviewed_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(document)
    return _document_read(document)


@router.post("/{document_id}/verify", response_model=DocumentRead)
async def verify_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_lead)],
    document: Annotated[Document, Depends(get_accessible_document)],
    payload: DocumentWorkflowUpdate | None = None,
) -> DocumentRead:
    """Verify a document as a lead engineer."""
    document.verified_by_id = current_user.id
    document.verified_at = datetime.now(UTC)
    document.workflow_status = DocumentWorkflowStatus.VERIFIED_BY_LEAD
    if payload is not None and payload.verification_notes is not None:
        document.verification_notes = payload.verification_notes
    await session.commit()
    await session.refresh(document)
    return _document_read(document)


@router.post("/{document_id}/request-revision", response_model=DocumentRead)
async def request_document_revision(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_lead)],
    document: Annotated[Document, Depends(get_accessible_document)],
    payload: DocumentWorkflowUpdate | None = None,
) -> DocumentRead:
    """Return a document to an engineer for revision."""
    requested_status = (
        payload.workflow_status
        if payload is not None and payload.workflow_status is not None
        else DocumentWorkflowStatus.ANALYZING
    )
    if requested_status not in {
        DocumentWorkflowStatus.ANALYZING,
        DocumentWorkflowStatus.REVIEWED_BY_ENGINEER,
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Revision status must be ANALYZING or REVIEWED_BY_ENGINEER.",
        )
    document.workflow_status = requested_status
    document.verification_notes = payload.verification_notes if payload is not None else None
    document.verified_by_id = None
    document.verified_at = None
    if requested_status == DocumentWorkflowStatus.ANALYZING:
        document.reviewed_at = None
    await session.commit()
    await session.refresh(document)
    return _document_read(document)


@router.get("", response_model=DocumentListResponse, responses=NOT_READY)
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentListResponse:
    """List documents visible to the current user."""

    query = select(Document).options(joinedload(Document.owner), joinedload(Document.assigned_to))
    if current_user.role not in {UserRole.LEAD_ENGINEER, UserRole.SUPERUSER}:
        query = query.where(Document.owner_id == current_user.id)
    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (
        (
            await session.execute(
                query
                .order_by(Document.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return DocumentListResponse(
        documents=[
            _document_read(d)
            for d in rows
        ],
        pagination=PageInfo(page=page, page_size=page_size, total=total),
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
    responses={**NOT_READY, 200: {"model": DocumentUploadResponse}},
)
async def upload_document(
    file: Annotated[UploadFile, File(description="Native-text PDF or DOCX")],
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentUploadResponse:
    """Persist a validated document and enqueue canonical extraction."""

    result = await upload_service.create_or_reuse(file, session)
    if not result.deduplicated:
        result.document.owner_id = current_user.id
        await session.commit()
        await session.refresh(result.document)
    if result.deduplicated:
        response.status_code = status.HTTP_200_OK
    else:
        await enqueue_extraction(result.document, session)
    return DocumentUploadResponse(
        id=result.document.id,
        filename=result.document.original_filename,
        status=result.document.status,
        created_at=result.document.created_at,
        deduplicated=result.deduplicated,
    )


@router.get("/{document_id}", response_model=DocumentRead, responses=NOT_READY)
async def get_document(
    document_id: UUID,
    document: Annotated[Document, Depends(get_accessible_document)],
) -> DocumentRead:
    """Return safe metadata for one document."""

    return _document_read(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def delete_document(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
) -> Response:
    """Permanently delete a document, its database records, storage files, and artifacts."""

    # 1. Clean up physical files from storage
    for uri in (document.storage_uri, document.canonical_pdf_uri):
        if uri:
            with contextlib.suppress(Exception):
                if uri.startswith(storage.scheme):
                    storage.delete(uri)
                else:
                    suffix = uri.split("://", 1)[-1] if "://" in uri else uri
                    target = storage.root / suffix
                    if target.exists() and target.is_file():
                        target.unlink()

    # 2. Clean up artifact directory
    artifacts_dir = storage.root / "artifacts" / str(document.id)
    if artifacts_dir.exists() and artifacts_dir.is_dir():
        with contextlib.suppress(OSError):
            shutil.rmtree(artifacts_dir, ignore_errors=True)

    # 3. Clean up database record (foreign keys cascade to stage_runs, issues, audit_events)
    await session.execute(delete(Document).where(Document.id == document_id))
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    responses=NOT_READY,
)
async def get_document_status(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> DocumentStatusResponse:
    """Return processing progress and latest stage states."""

    stage_runs = (
        (
            await session.execute(
                select(StageRun)
                .where(StageRun.document_id == document_id)
                .order_by(StageRun.created_at.asc(), StageRun.id.asc())
            )
        )
        .scalars()
        .all()
    )
    latest_by_stage: dict[str, StageRun] = {}
    for stage_run in stage_runs:
        stage_name = (
            PipelineStage.EXTRACTING.value
            if stage_run.stage_name == "extraction"
            else stage_run.stage_name
        )
        latest_by_stage[stage_name] = stage_run
    ordered_stage_runs = [
        latest_by_stage[stage.value] for stage in PipelineStage if stage.value in latest_by_stage
    ]
    ordered_stage_runs.extend(
        stage_run
        for stage_name, stage_run in latest_by_stage.items()
        if stage_name not in {stage.value for stage in PipelineStage}
    )
    completed = sum(
        1
        for stage_run in ordered_stage_runs
        if stage_run.status in (StageStatus.SUCCEEDED, StageStatus.SUCCEEDED_WITH_WARNINGS)
    )
    running_progress = max(
        (
            stage_run.progress_pct
            for stage_run in ordered_stage_runs
            if stage_run.status == StageStatus.RUNNING
        ),
        default=0,
    )
    calculated_progress = (
        100
        if document.status
        in {DocumentStatus.COMPLETED, DocumentStatus.COMPLETED_WITH_WARNINGS, DocumentStatus.FAILED}
        else min(99, int(((completed * 100) + running_progress) / len(PipelineStage)))
    )
    stage_reads = [StageRunRead.model_validate(r) for r in ordered_stage_runs]
    for stage_read in stage_reads:
        if stage_read.name == "extraction":
            stage_read.name = PipelineStage.EXTRACTING.value
    return DocumentStatusResponse(
        id=document.id,
        status=document.status,
        progress_pct=max(document.progress_pct, calculated_progress),
        stages=stage_reads,
        updated_at=document.updated_at,
    )


@router.get(
    "/{document_id}/issues",
    response_model=IssueListResponse,
    responses=NOT_READY,
)
async def list_document_issues(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
    category: IssueCategory | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> IssueListResponse:
    """List issues with optional canonical category filtering."""

    # Severity counts across all issues for this document
    counts_result = (
        await session.execute(
            select(Issue.severity, func.count(Issue.id))
            .where(Issue.document_id == document_id)
            .group_by(Issue.severity)
        )
    ).all()
    counts_by_severity: dict[Severity, int] = {s: 0 for s in Severity}
    for sev, count in counts_result:
        counts_by_severity[sev] = count

    # Filtered query for pagination
    query = select(Issue).where(Issue.document_id == document_id)
    if category is not None:
        query = query.where(Issue.category == category)

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    offset = (page - 1) * page_size
    issues = (
        (
            await session.execute(
                query.order_by(Issue.created_at.asc(), Issue.id.asc())
                .offset(offset)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    return IssueListResponse(
        issues=[IssueRead.model_validate(i) for i in issues],
        pagination=PageInfo(page=page, page_size=page_size, total=total),
        counts_by_severity=counts_by_severity,
    )


@router.get(
    "/{document_id}/pdf",
    response_class=FileResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document or canonical PDF not found",
        }
    },
)
async def get_document_pdf(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> FileResponse:
    """Stream the canonical PDF rendition of an uploaded document."""

    uri = document.canonical_pdf_uri or document.storage_uri
    if not uri:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canonical PDF rendition not available.",
        )

    key = uri
    if key.startswith(storage.scheme):
        key = key[len(storage.scheme) :]

    path = storage._path_for_key(key)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on storage.",
        )

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=f"{document.safe_filename}.pdf",
        content_disposition_type="inline",
    )


@router.get(
    "/{document_id}/traceability-summary",
    response_model=TraceabilitySummaryResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def get_traceability_summary(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> TraceabilitySummaryResponse:
    """Return traceability counts for audit triage."""

    issues = (
        (
            await session.execute(
                select(Issue).where(
                    Issue.document_id == document_id,
                    Issue.category == IssueCategory.TRACEABILITY,
                )
            )
        )
        .scalars()
        .all()
    )

    counts_by_type: dict[str, int] = {}
    counts_by_severity: dict[str, int] = {}
    critical_count = 0
    unresolved_count = 0

    for issue in issues:
        counts_by_type[issue.type] = counts_by_type.get(issue.type, 0) + 1
        sev_key = getattr(issue.severity, "value", str(issue.severity))
        counts_by_severity[sev_key] = counts_by_severity.get(sev_key, 0) + 1
        if issue.severity in {Severity.CRITICAL, "CRITICAL"}:
            critical_count += 1
        if issue.included_in_report:
            unresolved_count += 1

    return TraceabilitySummaryResponse(
        document_id=document.id,
        counts_by_type=counts_by_type,
        counts_by_severity=counts_by_severity,
        critical_count=critical_count,
        unresolved_count=unresolved_count,
    )


@router.get(
    "/{document_id}/report",
    response_model=ReviewReportPreview,
)
async def get_report_preview(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> ReviewReportPreview:
    """Return the current draft-report composition without generating a file."""
    issues = (
        (
            await session.execute(
                select(Issue).where(
                    Issue.document_id == document_id,
                    Issue.included_in_report.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    counts: dict[str, int] = {}
    blockers = 0
    for issue in issues:
        sev_key = getattr(issue.severity, "value", str(issue.severity))
        counts[sev_key] = counts.get(sev_key, 0) + 1
        if issue.severity in {
            Severity.BLOCKER,
            Severity.CRITICAL,
            Severity.HIGH,
            "BLOCKER",
            "CRITICAL",
            "HIGH",
        }:
            blockers += 1
    summary = (
        "Blockers require correction before reissue."
        if blockers
        else "No blocker findings are included in the draft report."
    )
    return ReviewReportPreview(
        document_id=document_id,
        included_findings=len(issues),
        blockers=blockers,
        counts_by_severity=counts,
        summary_judgement=summary,
    )


@router.get(
    "/{document_id}/export",
    response_class=Response,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def export_document(
    document_id: UUID,
    format: Annotated[str, Query(pattern=r"^(pdf|docx)$")],
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
    document: Annotated[Document, Depends(get_accessible_document)],
    include_minors: Annotated[
        bool, Query(description="Include minor and informational findings.")
    ] = False,
) -> Response:
    """Export the annotated original PDF or formal DOCX review report."""

    issues = (
        (
            await session.execute(
                select(Issue)
                .where(Issue.document_id == document_id)
                .order_by(Issue.created_at.asc(), Issue.id.asc())
            )
        )
        .scalars()
        .all()
    )

    safe_name = document.safe_filename
    if format == "pdf":
        selected_issues = [
            issue
            for issue in issues
            if issue.included_in_report
            and (
                include_minors
                or getattr(issue.severity, "value", str(issue.severity)).upper()
                not in {"MINOR", "INFO", "LOW"}
            )
        ]
        pdf_bytes = export_annotated_pdf(document, selected_issues, storage)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_annotated.pdf"'},
        )
    if format == "docx":
        refresh = getattr(session, "refresh", None)
        if refresh is not None:
            try:
                await refresh(document, ["owner", "verified_by"])
            except TypeError:
                # Lightweight test sessions and compatibility adapters may only
                # implement SQLAlchemy's single-argument refresh form.
                await refresh(document)
        scorecard: dict[str, Any] | None = None
        scorecard_path = storage._path_for_key(f"artifacts/{document.id}/budinski_scorecard.json")
        if scorecard_path.exists():
            try:
                scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                scorecard = None
        assessment = assessment_from_document_findings(
            document, list(issues), scorecard_data=scorecard, include_minors=include_minors
        )
        docx_bytes = generate_ale_review_docx(assessment, document)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_review.docx"'},
        )
    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


@router.get(
    "/{document_id}/events",
    response_class=StreamingResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def stream_document_events(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    document: Annotated[Document, Depends(get_accessible_document)],
) -> StreamingResponse:
    """Stream real-time processing progress and stage transitions via Server-Sent Events (SSE)."""

    TERMINAL_STATUSES = {
        DocumentStatus.COMPLETED,
        DocumentStatus.COMPLETED_WITH_WARNINGS,
        DocumentStatus.FAILED,
    }
    POLL_INTERVAL = 2.0  # seconds between DB polls
    MAX_POLL_DURATION = 600  # 10 minutes max SSE lifetime

    async def event_generator() -> AsyncIterator[str]:
        elapsed = 0.0
        while elapsed < MAX_POLL_DURATION:
            async with async_session_factory() as poll_session:
                doc = (
                    await poll_session.execute(select(Document).where(Document.id == document_id))
                ).scalar_one_or_none()
                if doc is None:
                    yield "event: close\ndata: {}\n\n"
                    return

                stages_res = (
                    (
                        await poll_session.execute(
                            select(StageRun)
                            .where(StageRun.document_id == document_id)
                            .order_by(StageRun.created_at.asc())
                        )
                    )
                    .scalars()
                    .all()
                )

            latest_stages: dict[str, StageRun] = {}
            for stage_run in stages_res:
                stage_name = (
                    PipelineStage.EXTRACTING.value
                    if stage_run.stage_name == "extraction"
                    else stage_run.stage_name
                )
                latest_stages[stage_name] = stage_run
            ordered_stages = [
                latest_stages[stage.value]
                for stage in PipelineStage
                if stage.value in latest_stages
            ]
            ordered_stages.extend(
                stage_run
                for stage_name, stage_run in latest_stages.items()
                if stage_name not in {stage.value for stage in PipelineStage}
            )
            completed_stages = sum(
                1
                for s in ordered_stages
                if s.status in (StageStatus.SUCCEEDED, StageStatus.SUCCEEDED_WITH_WARNINGS)
            )
            total_pipeline_stages = 6
            pct = (
                100
                if doc.status in TERMINAL_STATUSES
                else min(95, int((completed_stages / total_pipeline_stages) * 100))
            )

            payload = {
                "document_id": str(doc.id),
                "status": doc.status.value,
                "progress_pct": pct,
                "stages": [
                    {
                        "name": PipelineStage.EXTRACTING.value
                        if s.stage_name == "extraction"
                        else s.stage_name,
                        "status": s.status.value,
                        "progress_pct": s.progress_pct,
                    }
                    for s in ordered_stages
                ],
            }
            yield f"event: progress\ndata: {json.dumps(payload)}\n\n"

            if doc.status in TERMINAL_STATUSES:
                yield "event: close\ndata: {}\n\n"
                return

            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

        # Timeout — close the SSE stream gracefully
        yield "event: close\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
