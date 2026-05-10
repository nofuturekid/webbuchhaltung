import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.models.user import User
from app.schemas.document import (
    BookingSuggestion,
    ConfirmDocumentRequest,
    DocumentListResponse,
    DocumentResponse,
)
from app.services import document as document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    doc = await document_service.upload_document(
        session, file, mandant_id, current_user.id
    )
    return DocumentResponse.model_validate(doc)


@router.post("/{doc_id}/process", response_model=DocumentResponse)
async def process_document(
    doc_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    doc = await document_service.process_document(
        session, doc_id, mandant_id, current_user.id
    )
    return DocumentResponse.model_validate(doc)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    doc = await document_service.get_document(session, doc_id, mandant_id)
    return DocumentResponse.model_validate(doc)


@router.get("/{doc_id}/file")
async def download_document_file(
    doc_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> Response:
    doc = await document_service.get_document(session, doc_id, mandant_id)
    from app.services.document_storage import read_file

    content = read_file(doc.storage_path)
    return Response(content=content, media_type=doc.mime_type)


@router.get("/{doc_id}/suggestion", response_model=BookingSuggestion)
async def get_booking_suggestion(
    doc_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BookingSuggestion:
    return await document_service.get_booking_suggestion(session, doc_id, mandant_id)


@router.post("/{doc_id}/confirm", response_model=DocumentResponse)
async def confirm_document(
    doc_id: uuid.UUID,
    payload: ConfirmDocumentRequest,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    doc = await document_service.confirm_document(
        session, doc_id, mandant_id, current_user.id, payload
    )
    return DocumentResponse.model_validate(doc)


@router.post("/{doc_id}/reject", response_model=DocumentResponse)
async def reject_document(
    doc_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    doc = await document_service.reject_document(
        session, doc_id, mandant_id, current_user.id
    )
    return DocumentResponse.model_validate(doc)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    return await document_service.list_documents(
        session, mandant_id, page=page, page_size=page_size, status=status
    )
