import uuid
from decimal import Decimal

from pydantic import BaseModel


class AccountCreate(BaseModel):
    account_number: str
    name: str
    account_class: str
    tax_type: str | None = None


class AccountUpdate(BaseModel):
    private_share_percent: int | None = None
    is_active: bool | None = None
    name: str | None = None
    tax_type: str | None = None


class AccountResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    account_number: str
    name: str
    account_class: str
    tax_type: str | None
    skr_variant: str
    is_custom: bool
    private_share_percent: int
    is_active: bool


class AccountBalanceResponse(BaseModel):
    account_id: uuid.UUID
    account_number: str
    debit_cents: int
    credit_cents: int
    balance_cents: int


class TaxKeyResponse(BaseModel):
    model_config = {"from_attributes": True}

    code: int
    description: str
    tax_rate: Decimal | None
    tax_type: str
