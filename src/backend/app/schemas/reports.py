import uuid

from pydantic import BaseModel


class EURLineItem(BaseModel):
    account_number: str
    account_name: str
    gross_cents: int
    tax_cents: int
    net_cents: int
    private_deduction_cents: int
    reportable_cents: int


class EURResponse(BaseModel):
    date_from: str
    date_to: str
    betriebseinnahmen_cents: int
    betriebsausgaben_cents: int
    ust_cents: int
    vst_19_cents: int
    vst_7_cents: int
    items: list[EURLineItem]


class KontoauszugLine(BaseModel):
    booking_id: uuid.UUID
    date_booking: str
    document_number: str | None
    notes: str | None
    debit_cents: int
    credit_cents: int
    running_balance_cents: int
    entry_number: int | None
    status: str


class KontoauszugResponse(BaseModel):
    account_id: uuid.UUID
    account_number: str
    account_name: str
    date_from: str
    date_to: str
    opening_balance_cents: int
    closing_balance_cents: int
    lines: list[KontoauszugLine]
