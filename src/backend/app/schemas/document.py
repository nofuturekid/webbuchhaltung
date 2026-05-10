import uuid
from datetime import date, datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    filename: str
    storage_path: str
    mime_type: str
    file_size_bytes: int
    status: str
    extracted_json: dict | None
    booking_id: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime


class ExtractionResult(BaseModel):
    vendor_name: str | None = None
    document_date: date | None = None
    total_amount_cents: int | None = None
    vat_amount_cents: int | None = None
    suggested_debit_account: str | None = None  # 4-digit SKR number
    suggested_credit_account: str | None = None
    booking_text: str | None = None  # max 60 chars
    confidence_score: float = 0.0


class BookingSuggestion(BaseModel):
    extraction: ExtractionResult
    debit_coa_id: uuid.UUID | None = None
    credit_coa_id: uuid.UUID | None = None


class ConfirmDocumentRequest(BaseModel):
    debit_coa_id: uuid.UUID
    credit_coa_id: uuid.UUID
    amount_cents: int
    booking_text: str
    booking_date: date
    tax_key_code: int | None = None  # integer FK to tax_keys.code


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
