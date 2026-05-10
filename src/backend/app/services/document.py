import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import (
    ConflictError,
    DocumentAlreadyBookedError,
    NotFoundError,
    UnsupportedFileTypeError,
)
from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.models.document import Document
from app.schemas.document import (
    BookingSuggestion,
    ConfirmDocumentRequest,
    DocumentListResponse,
    DocumentResponse,
    ExtractionResult,
)
from app.services import booking as booking_service
from app.services.audit import write_audit
from app.services.document_storage import read_file, save_file
from app.services.llm_extraction import extract_document
from app.services.period import get_or_create_period

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}


async def upload_document(
    session: AsyncSession,
    file: UploadFile,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    """Save an uploaded file and create a Document record."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise UnsupportedFileTypeError(f"Unsupported file type: {file.content_type}")
    content = await file.read()
    storage_path = save_file(content, file.filename or "upload", mandant_id)
    doc = Document(
        mandant_id=mandant_id,
        filename=file.filename or "upload",
        storage_path=storage_path,
        mime_type=file.content_type,
        file_size_bytes=len(content),
        created_by=user_id,
    )
    session.add(doc)
    await session.flush()
    await write_audit(
        session,
        table_name="documents",
        record_id=doc.id,
        action="insert",
        change_summary={},
        mandant_id=mandant_id,
        user_id=user_id,
    )
    return doc


async def process_document(
    session: AsyncSession,
    doc_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    """Run LLM extraction on a document and store the result."""
    doc = await _get_doc(session, doc_id, mandant_id)
    content = read_file(doc.storage_path)
    accounts_result = await session.execute(
        select(ChartOfAccount.account_number).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.is_active.is_(True),
        )
    )
    known_accounts = [row[0] for row in accounts_result.fetchall()]
    result = await extract_document(content, doc.mime_type, known_accounts)
    doc.extracted_json = result.model_dump()
    doc.status = "processed"
    doc.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await write_audit(
        session,
        table_name="documents",
        record_id=doc.id,
        action="update",
        change_summary={"status": ["uploaded", "processed"]},
        mandant_id=mandant_id,
        user_id=user_id,
    )
    return doc


async def get_document(
    session: AsyncSession, doc_id: uuid.UUID, mandant_id: uuid.UUID
) -> Document:
    """Fetch a single document, scoped to the mandant."""
    return await _get_doc(session, doc_id, mandant_id)


async def get_booking_suggestion(
    session: AsyncSession, doc_id: uuid.UUID, mandant_id: uuid.UUID
) -> BookingSuggestion:
    """Return a booking suggestion derived from the extracted document data."""
    doc = await _get_doc(session, doc_id, mandant_id)
    extraction = ExtractionResult(**(doc.extracted_json or {}))

    debit_coa_id = await _lookup_account(
        session, mandant_id, extraction.suggested_debit_account
    )
    credit_coa_id = await _lookup_account(
        session, mandant_id, extraction.suggested_credit_account
    )

    return BookingSuggestion(
        extraction=extraction,
        debit_coa_id=debit_coa_id,
        credit_coa_id=credit_coa_id,
    )


async def confirm_document(
    session: AsyncSession,
    doc_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ConfirmDocumentRequest,
) -> Document:
    """Create a posted Booking from confirmed document data and link it to the document."""
    doc = await _get_doc(session, doc_id, mandant_id)
    if doc.status == "booked":
        raise DocumentAlreadyBookedError()
    if doc.status != "processed":
        raise ConflictError(
            f"Document must be in 'processed' state, got '{doc.status}'."
        )

    period = await get_or_create_period(
        session, mandant_id, data.booking_date.year, data.booking_date.month
    )
    from app.errors import PeriodLockedError

    if period.status in ("locked", "archived"):
        raise PeriodLockedError()

    booking_obj = Booking(
        mandant_id=mandant_id,
        booking_type="entry",
        date_booking=data.booking_date,
        amount_cents=data.amount_cents,
        notes=data.booking_text[:60],
        coa_id=data.debit_coa_id,
        counter_coa_id=data.credit_coa_id,
        tax_key_code=data.tax_key_code,
        status="draft",
        created_by=user_id,
    )
    session.add(booking_obj)
    await session.flush()

    entry_number = await booking_service.get_next_entry_number(session, mandant_id)
    booking_obj.status = "posted"
    booking_obj.entry_number = entry_number

    await write_audit(
        session,
        table_name="bookings",
        record_id=booking_obj.id,
        action="update",
        change_summary={
            "transition": "draft→posted",
            "status": ["draft", "posted"],
            "entry_number": [None, entry_number],
            "source": "document_capture",
        },
        mandant_id=mandant_id,
        user_id=user_id,
    )
    await session.flush()

    doc.booking_id = booking_obj.id
    doc.status = "booked"
    doc.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await write_audit(
        session,
        table_name="documents",
        record_id=doc.id,
        action="update",
        change_summary={
            "status": ["processed", "booked"],
            "booking_id": str(booking_obj.id),
        },
        mandant_id=mandant_id,
        user_id=user_id,
    )
    return doc


async def reject_document(
    session: AsyncSession,
    doc_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    """Mark a document as rejected."""
    doc = await _get_doc(session, doc_id, mandant_id)
    doc.status = "rejected"
    doc.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await write_audit(
        session,
        table_name="documents",
        record_id=doc.id,
        action="update",
        change_summary={"status": [doc.status, "rejected"]},
        mandant_id=mandant_id,
        user_id=user_id,
    )
    return doc


async def list_documents(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
) -> DocumentListResponse:
    """Return a paginated list of documents for a mandant."""
    q = select(Document).where(Document.mandant_id == mandant_id)
    if status:
        q = q.where(Document.status == status)
    total_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(total_q)).scalar_one()
    items_q = (
        q.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await session.execute(items_q)).scalars().all()
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


async def _get_doc(
    session: AsyncSession, doc_id: uuid.UUID, mandant_id: uuid.UUID
) -> Document:
    """Fetch a document by id, scoped to the mandant. Raises NotFoundError if absent."""
    doc = (
        await session.execute(
            select(Document).where(
                Document.id == doc_id, Document.mandant_id == mandant_id
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        raise NotFoundError(f"Document {doc_id} not found.")
    return doc


async def _lookup_account(
    session: AsyncSession, mandant_id: uuid.UUID, account_number: str | None
) -> uuid.UUID | None:
    """Return the ChartOfAccount.id for a given account number, or None if not found."""
    if not account_number:
        return None
    result = (
        await session.execute(
            select(ChartOfAccount.id).where(
                ChartOfAccount.mandant_id == mandant_id,
                ChartOfAccount.account_number == account_number,
            )
        )
    ).scalar_one_or_none()
    return result
