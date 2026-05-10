import uuid
from datetime import date

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


# --- Saldenliste (Trial Balance) ---


class SaldenlisteRow(BaseModel):
    account_number: str
    account_name: str
    opening_balance_cents: int
    period_debit_cents: int
    period_credit_cents: int
    closing_balance_cents: int


class SaldenlisteResponse(BaseModel):
    date_from: date
    date_to: date
    rows: list[SaldenlisteRow]
    total_debit_cents: int
    total_credit_cents: int


# --- Bilanz (Balance Sheet, HGB §266) ---


class BilanzSection(BaseModel):
    label: str
    amount_cents: int
    subsections: list["BilanzSection"] = []


class BilanzResponse(BaseModel):
    as_of_date: date
    aktiva: list[BilanzSection]
    passiva: list[BilanzSection]
    aktiva_total_cents: int
    passiva_total_cents: int
    balanced: bool
    imbalance_cents: int


# --- G+V (Gewinn- und Verlustrechnung) ---


class GuvRow(BaseModel):
    label: str
    account_numbers: list[str]
    amount_cents: int


class GuvResponse(BaseModel):
    date_from: date
    date_to: date
    revenue_rows: list[GuvRow]
    expense_rows: list[GuvRow]
    revenue_total_cents: int
    expense_total_cents: int
    result_cents: int


# --- BWA (Betriebswirtschaftliche Auswertung) ---


class BWAColumn(BaseModel):
    year: int
    month: int
    revenue_cents: int
    material_costs_cents: int
    personnel_costs_cents: int
    other_costs_cents: int
    ebit_cents: int


class BWAResponse(BaseModel):
    year: int
    columns: list[BWAColumn]
    ytd_revenue_cents: int
    ytd_ebit_cents: int
