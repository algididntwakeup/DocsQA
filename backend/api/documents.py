import contextlib
import json
import shutil
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_storage, get_upload_service
from db.session import get_session
from domain.enums import DocumentStatus, IssueCategory, Severity, StageStatus
from models.audit import AuditEvent
from models.document import Document, StageRun
from models.issue import Issue
from schemas.audit import (
    AuditEventListResponse,
    AuditEventRead,
    DocumentDispositionRequest,
)
from schemas.common import PageInfo, ProblemDetail
from schemas.documents import (
    DocumentListResponse,
    DocumentRead,
    DocumentStatusResponse,
    DocumentUploadResponse,
    StageRunRead,
    TraceabilitySummaryResponse,
)
from schemas.issues import IssueListResponse, IssueRead
from services.export import (
    export_annotated_pdf,
    export_csv_issues,
    export_excel_workbook,
    export_json_audit_bundle,
)
from services.pipeline import enqueue_extraction
from services.storage.local import LocalStorage
from services.uploads import UploadService

router = APIRouter(prefix="/documents", tags=["documents"])


NOT_READY: dict[int | str, dict[str, Any]] = {
    501: {"model": ProblemDetail, "description": "Feature not implemented"}
}


@router.get("", response_model=DocumentListResponse, responses=NOT_READY)
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentListResponse:
    """List documents visible to the current user."""

    total = (await session.execute(select(func.count(Document.id)))).scalar_one()
    rows = (
        (
            await session.execute(
                select(Document)
                .order_by(Document.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return DocumentListResponse(
        documents=[DocumentRead.model_validate(d) for d in rows],
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
) -> DocumentUploadResponse:
    """Persist a validated document and enqueue canonical extraction."""

    result = await upload_service.create_or_reuse(file, session)
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentRead:
    """Return safe metadata for one document."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentRead.model_validate(document)


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
    storage: Annotated[LocalStorage, Depends(get_storage)],
) -> Response:
    """Permanently delete a document, its database records, storage files, and artifacts."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

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
) -> DocumentStatusResponse:
    """Return processing progress and latest stage states."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    stage_runs = (
        (
            await session.execute(
                select(StageRun)
                .where(StageRun.document_id == document_id)
                .order_by(StageRun.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return DocumentStatusResponse(
        id=document.id,
        status=document.status,
        review_status=document.review_status,
        progress_pct=document.progress_pct,
        stages=[StageRunRead.model_validate(r) for r in stage_runs],
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
    category: IssueCategory | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> IssueListResponse:
    """List issues with optional canonical category filtering."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

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
) -> FileResponse:
    """Stream the canonical PDF rendition of an uploaded document."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

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


@router.post(
    "/{document_id}/disposition",
    response_model=DocumentRead,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def set_document_disposition(
    document_id: UUID,
    payload: DocumentDispositionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentRead:
    """Apply final Lead Reviewer disposition to an audited document."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    previous_state = {"review_status": document.review_status.value}
    document.review_status = payload.disposition
    new_state = {"review_status": document.review_status.value}

    audit_event = AuditEvent(
        document_id=document.id,
        issue_id=None,
        actor_id=payload.actor_id,
        actor_role=payload.actor_role,
        action="DOCUMENT_DISPOSITION",
        previous_state=previous_state,
        new_state=new_state,
        notes=payload.justification,
    )
    session.add(audit_event)
    await session.commit()
    await session.refresh(document)

    return DocumentRead.model_validate(document)


@router.get(
    "/{document_id}/audit-events",
    response_model=AuditEventListResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ProblemDetail,
            "description": "Document not found",
        }
    },
)
async def list_document_audit_events(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuditEventListResponse:
    """List immutable audit events for an audited document in chronological order."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    events = (
        (
            await session.execute(
                select(AuditEvent)
                .where(AuditEvent.document_id == document_id)
                .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
            )
        )
        .scalars()
        .all()
    )

    return AuditEventListResponse(
        events=[AuditEventRead.model_validate(e) for e in events],
        total=len(events),
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
) -> TraceabilitySummaryResponse:
    """Return traceability counts for audit triage."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

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
        sev_key = issue.severity.value
        counts_by_severity[sev_key] = counts_by_severity.get(sev_key, 0) + 1
        if issue.severity == Severity.CRITICAL:
            critical_count += 1
        if issue.decision is None:
            unresolved_count += 1

    return TraceabilitySummaryResponse(
        document_id=document.id,
        counts_by_type=counts_by_type,
        counts_by_severity=counts_by_severity,
        critical_count=critical_count,
        unresolved_count=unresolved_count,
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
    format: Annotated[str, Query(pattern=r"^(pdf|xlsx|csv|json)$")],
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[LocalStorage, Depends(get_storage)],
) -> Response:
    """Export the annotated rendition or structured issue log in PDF, XLSX, CSV, or JSON format."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

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

    audit_events = (
        (
            await session.execute(
                select(AuditEvent)
                .where(AuditEvent.document_id == document_id)
                .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
            )
        )
        .scalars()
        .all()
    )

    safe_name = document.safe_filename
    if format == "pdf":
        pdf_bytes = export_annotated_pdf(document, list(issues), storage)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_annotated.pdf"'},
        )
    elif format == "xlsx":
        xlsx_bytes = export_excel_workbook(document, list(issues), list(audit_events))
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_issues.xlsx"'},
        )
    elif format == "csv":
        csv_str = export_csv_issues(document, list(issues))
        return Response(
            content=csv_str,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_issues.csv"'},
        )
    elif format == "json":
        bundle = export_json_audit_bundle(document, list(issues), list(audit_events))
        return JSONResponse(
            content=bundle,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}_audit_bundle.json"'
            },
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
) -> StreamingResponse:
    """Stream real-time processing progress and stage transitions via Server-Sent Events (SSE)."""

    document = (
        await session.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    stages_res = (
        (
            await session.execute(
                select(StageRun)
                .where(StageRun.document_id == document_id)
                .order_by(StageRun.created_at.asc())
            )
        )
        .scalars()
        .all()
    )

    completed_stages = sum(
        1
        for s in stages_res
        if s.status in (StageStatus.SUCCEEDED, StageStatus.SUCCEEDED_WITH_WARNINGS)
    )
    total_pipeline_stages = 10
    pct = (
        100
        if document.status
        in (DocumentStatus.COMPLETED, DocumentStatus.COMPLETED_WITH_WARNINGS, DocumentStatus.FAILED)
        else min(95, int((completed_stages / total_pipeline_stages) * 100))
    )

    initial_payload = {
        "document_id": str(document.id),
        "status": document.status.value,
        "progress_pct": pct,
        "stages": [{"name": s.stage_name, "status": s.status.value} for s in stages_res],
    }

    async def event_generator() -> AsyncIterator[str]:
        yield f"event: progress\ndata: {json.dumps(initial_payload)}\n\n"
        if document.status in (
            DocumentStatus.COMPLETED,
            DocumentStatus.COMPLETED_WITH_WARNINGS,
            DocumentStatus.FAILED,
        ):
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
