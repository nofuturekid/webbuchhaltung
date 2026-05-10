import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator


class BookingCreate(BaseModel):
    booking_type: Literal["bank", "entry"] = "entry"
    date_booking: date
    date_tax: date | None = None
    amount_cents: int
    currency: str = "EUR"
    document_number: str | None = None
    notes: str | None = None
    booking_group_id: uuid.UUID | None = None
    coa_id: uuid.UUID | None = None
    counter_coa_id: uuid.UUID | None = None
    tax_rate: Decimal | None = None
    tax_amount_cents: int | None = None
    tax_key_code: int | None = None

    @field_validator("amount_cents")
    @classmethod
    def amount_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount_cents must be positive")
        return v

    @field_validator("notes")
    @classmethod
    def notes_max_60(cls, v: str | None) -> str | None:
        if v and len(v) > 60:
            raise ValueError("notes must be ≤60 characters (DATEV Buchungstext limit)")
        return v


class BookingUpdate(BaseModel):
    date_booking: date | None = None
    date_tax: date | None = None
    amount_cents: int | None = None
    document_number: str | None = None
    notes: str | None = None
    coa_id: uuid.UUID | None = None
    counter_coa_id: uuid.UUID | None = None
    tax_rate: Decimal | None = None
    tax_amount_cents: int | None = None
    tax_key_code: int | None = None

    @field_validator("amount_cents")
    @classmethod
    def amount_must_be_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("amount_cents must be positive")
        return v

    @field_validator("notes")
    @classmethod
    def notes_max_60(cls, v: str | None) -> str | None:
        if v and len(v) > 60:
            raise ValueError("notes must be ≤60 characters (DATEV Buchungstext limit)")
        return v


class BookingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    booking_type: str
    status: str
    date_booking: date
    date_tax: date | None
    amount_cents: int
    currency: str
    document_number: str | None
    notes: str | None
    entry_number: int | None
    coa_id: uuid.UUID | None
    counter_coa_id: uuid.UUID | None
    tax_rate: Decimal | None
    tax_amount_cents: int | None
    tax_key_code: int | None
    booking_group_id: uuid.UUID | None
    parent_booking_id: uuid.UUID | None
    reversal_of_id: uuid.UUID | None
    created_by: uuid.UUID


class BookingListResponse(BaseModel):
    items: list[BookingResponse]
    total: int
    page: int
    page_size: int


class BookingGroupCreate(BaseModel):
    description: str | None = None


class BookingGroupResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    description: str | None
