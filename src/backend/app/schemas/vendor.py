import uuid
from datetime import date

from pydantic import BaseModel, field_validator


class VendorCreate(BaseModel):
    name: str
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str = "DE"
    vat_id: str | None = None
    email: str | None = None
    bank_iban: str | None = None
    bank_bic: str | None = None


class VendorUpdate(BaseModel):
    name: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
    vat_id: str | None = None
    email: str | None = None
    bank_iban: str | None = None
    bank_bic: str | None = None


class VendorResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    name: str
    street: str | None
    postal_code: str | None
    city: str | None
    country: str
    vat_id: str | None
    email: str | None
    bank_iban: str | None
    bank_bic: str | None


class VendorListResponse(BaseModel):
    items: list[VendorResponse]
    total: int
    page: int
    page_size: int


class VendorInvoiceCreate(BaseModel):
    vendor_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    due_date: date | None = None
    amount_cents: int
    vat_amount_cents: int = 0
    currency: str = "EUR"
    notes: str | None = None
    document_id: uuid.UUID | None = None

    @field_validator("amount_cents")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount_cents must be > 0")
        return v


class VendorInvoicePostRequest(BaseModel):
    expense_coa_id: uuid.UUID  # SOLL: expense account chosen by user
    vat_coa_id: uuid.UUID | None = None  # SOLL: Vorsteuer account (UStG §15), optional


class VendorInvoiceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    vendor_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    due_date: date | None
    amount_cents: int
    vat_amount_cents: int
    currency: str
    status: str
    booking_id: uuid.UUID | None
    document_id: uuid.UUID | None
    notes: str | None
    created_by: uuid.UUID


class VendorInvoiceListResponse(BaseModel):
    items: list[VendorInvoiceResponse]
    total: int
    page: int
    page_size: int


class SepaExportRequest(BaseModel):
    due_on_or_before: date
