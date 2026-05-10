import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, field_validator


class CustomerCreate(BaseModel):
    name: str
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str = "DE"
    vat_id: str | None = None
    email: EmailStr | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
    vat_id: str | None = None
    email: EmailStr | None = None


class CustomerResponse(BaseModel):
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


class LineItemCreate(BaseModel):
    position: int
    description: str
    quantity: Decimal
    unit: str | None = None
    unit_price_cents: int
    vat_rate: Decimal

    @field_validator("vat_rate")
    @classmethod
    def validate_vat_rate(cls, v: Decimal) -> Decimal:
        allowed = {Decimal("0.00"), Decimal("0.07"), Decimal("0.19")}
        if v not in allowed:
            raise ValueError("vat_rate must be 0.00, 0.07, or 0.19")
        return v


class LineItemResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    invoice_id: uuid.UUID
    position: int
    description: str
    quantity: Decimal
    unit: str | None
    unit_price_cents: int
    vat_rate: Decimal
    net_total_cents: int | None
    vat_amount_cents: int | None


class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    issue_date: date | None = None
    due_date: date | None = None
    notes: str | None = None
    line_items: list[LineItemCreate]

    @field_validator("line_items")
    @classmethod
    def at_least_one_item(cls, v: list[LineItemCreate]) -> list[LineItemCreate]:
        if not v:
            raise ValueError("At least one line item is required.")
        return v


class InvoiceUpdate(BaseModel):
    customer_id: uuid.UUID | None = None
    issue_date: date | None = None
    due_date: date | None = None
    notes: str | None = None
    line_items: list[LineItemCreate] | None = None


class InvoiceListItem(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    invoice_number: str
    status: str
    customer_id: uuid.UUID
    issue_date: date | None
    due_date: date | None
    gross_total_cents: int | None
    currency: str


class InvoiceListResponse(BaseModel):
    items: list[InvoiceListItem]
    total: int
    page: int
    page_size: int


class InvoiceResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    mandant_id: uuid.UUID
    customer_id: uuid.UUID
    invoice_number: str
    status: str
    issue_date: date | None
    due_date: date | None
    currency: str
    net_total_cents: int | None
    vat_total_cents: int | None
    gross_total_cents: int | None
    notes: str | None
    booking_id: uuid.UUID | None
    line_items: list[LineItemResponse] = []


class SendEmailRequest(BaseModel):
    override_email: EmailStr | None = None


class InvoiceTemplateResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    mandant_id: uuid.UUID
    primary_color: str
    font_family: str
    header_text: str | None
    footer_text: str | None
    payment_terms_text: str


class InvoiceTemplateUpdate(BaseModel):
    primary_color: str | None = None
    font_family: str | None = None
    header_text: str | None = None
    footer_text: str | None = None
    payment_terms_text: str | None = None


class InvoiceSequenceResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    mandant_id: uuid.UUID
    prefix: str
    next_number: int
    year_reset: bool
    last_reset_year: int | None


class InvoiceSequenceUpdate(BaseModel):
    prefix: str | None = None
    year_reset: bool | None = None


class MandantSettingsUpdate(BaseModel):
    iban: str | None = None
    bic: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_from_name: str | None = None


class SmtpTestRequest(BaseModel):
    override_email: EmailStr | None = None
