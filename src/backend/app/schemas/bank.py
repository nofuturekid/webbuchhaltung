import uuid
from datetime import date, datetime

from pydantic import BaseModel


class BankAccountCreate(BaseModel):
    name: str
    iban: str
    bic: str | None = None
    currency: str = "EUR"


class BankAccountUpdate(BaseModel):
    name: str | None = None
    iban: str | None = None
    bic: str | None = None
    currency: str | None = None
    is_active: bool | None = None


class BankAccountResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    name: str
    iban: str
    bic: str | None
    currency: str
    is_active: bool
    created_at: datetime


class CsvColumnMap(BaseModel):
    date_col: str
    amount_col: str
    purpose_col: str | None = None
    counterpart_name_col: str | None = None
    counterpart_iban_col: str | None = None
    date_format: str = "%d.%m.%Y"
    decimal_separator: str = ","
    encoding: str = "utf-8-sig"
    skip_rows: int = 0


class BankTransactionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    bank_account_id: uuid.UUID
    transaction_date: date
    value_date: date | None
    amount_cents: int
    currency: str
    purpose: str | None
    counterpart_name: str | None
    counterpart_iban: str | None
    source_format: str
    status: str
    booking_id: uuid.UUID | None


class BankTransactionListResponse(BaseModel):
    items: list[BankTransactionResponse]
    total: int
    page: int
    page_size: int


class ImportStatsResponse(BaseModel):
    imported: int
    skipped: int  # duplicates


class MatchRequest(BaseModel):
    booking_id: uuid.UUID


class MatchCandidateResponse(BaseModel):
    booking_id: uuid.UUID
    booking_date: date
    amount_cents: int
    description: str | None
    entry_number: int
    score: float
