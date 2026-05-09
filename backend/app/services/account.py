import json
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AccountNotEditableError, NotFoundError
from app.models.account import ChartOfAccount, TaxKey
from app.models.booking import Booking
from app.schemas.account import AccountBalanceResponse, AccountCreate, AccountUpdate

SEED_DIR = Path(__file__).parent.parent.parent / "seed"


async def seed_skr_for_mandant(
    session: AsyncSession, mandant_id: uuid.UUID, skr_variant: str
) -> None:
    filename = SEED_DIR / f"{skr_variant}.json"
    accounts_data = json.loads(filename.read_text())
    for acc in accounts_data:
        obj = ChartOfAccount(
            mandant_id=mandant_id,
            account_number=acc["account_number"],
            name=acc["name"],
            account_class=acc["account_class"],
            tax_type=acc.get("tax_type"),
            skr_variant=skr_variant,
            is_custom=False,
        )
        session.add(obj)
    await session.flush()


async def list_accounts(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    account_class: str | None = None,
    is_active: bool | None = None,
) -> list[ChartOfAccount]:
    q = select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant_id)
    if account_class:
        q = q.where(ChartOfAccount.account_class == account_class)
    if is_active is not None:
        q = q.where(ChartOfAccount.is_active == is_active)
    result = await session.execute(q.order_by(ChartOfAccount.account_number))
    return list(result.scalars().all())


async def get_account(
    session: AsyncSession, account_id: uuid.UUID, mandant_id: uuid.UUID
) -> ChartOfAccount:
    result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.id == account_id,
            ChartOfAccount.mandant_id == mandant_id,
        )
    )
    acc = result.scalar_one_or_none()
    if not acc:
        raise NotFoundError(f"Account {account_id} not found.")
    return acc


async def create_custom_account(
    session: AsyncSession, mandant_id: uuid.UUID, data: AccountCreate
) -> ChartOfAccount:
    acc = ChartOfAccount(
        mandant_id=mandant_id,
        account_number=data.account_number,
        name=data.name,
        account_class=data.account_class,
        tax_type=data.tax_type,
        skr_variant="custom",
        is_custom=True,
    )
    session.add(acc)
    await session.flush()
    await session.refresh(acc)
    return acc


async def update_account(
    session: AsyncSession,
    account_id: uuid.UUID,
    mandant_id: uuid.UUID,
    data: AccountUpdate,
) -> ChartOfAccount:
    acc = await get_account(session, account_id, mandant_id)
    updates = data.model_dump(exclude_unset=True)
    if not acc.is_custom:
        allowed = {"private_share_percent", "is_active"}
        disallowed = set(updates) - allowed
        if disallowed:
            raise AccountNotEditableError()
    for field, value in updates.items():
        setattr(acc, field, value)
    await session.flush()
    await session.refresh(acc)
    return acc


async def deactivate_account(
    session: AsyncSession, account_id: uuid.UUID, mandant_id: uuid.UUID
) -> None:
    acc = await get_account(session, account_id, mandant_id)
    if not acc.is_custom:
        raise AccountNotEditableError()
    acc.is_active = False
    await session.flush()


async def list_tax_keys(session: AsyncSession) -> list[TaxKey]:
    result = await session.execute(select(TaxKey).order_by(TaxKey.code))
    return list(result.scalars().all())


async def get_tax_key(session: AsyncSession, code: int) -> TaxKey:
    result = await session.execute(select(TaxKey).where(TaxKey.code == code))
    tk = result.scalar_one_or_none()
    if not tk:
        raise NotFoundError(f"TaxKey {code} not found.")
    return tk


async def get_account_balance(
    session: AsyncSession,
    account_id: uuid.UUID,
    mandant_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
) -> AccountBalanceResponse:
    acc = await get_account(session, account_id, mandant_id)
    q_debit = select(func.coalesce(func.sum(Booking.amount_cents), 0)).where(
        Booking.coa_id == account_id,
        Booking.mandant_id == mandant_id,
        Booking.status == "posted",
    )
    q_credit = select(func.coalesce(func.sum(Booking.amount_cents), 0)).where(
        Booking.counter_coa_id == account_id,
        Booking.mandant_id == mandant_id,
        Booking.status == "posted",
    )
    if date_from:
        q_debit = q_debit.where(Booking.date_booking >= date_from)
        q_credit = q_credit.where(Booking.date_booking >= date_from)
    if date_to:
        q_debit = q_debit.where(Booking.date_booking <= date_to)
        q_credit = q_credit.where(Booking.date_booking <= date_to)
    debit = (await session.execute(q_debit)).scalar() or 0
    credit = (await session.execute(q_credit)).scalar() or 0
    return AccountBalanceResponse(
        account_id=account_id,
        account_number=acc.account_number,
        debit_cents=int(debit),
        credit_cents=int(credit),
        balance_cents=int(debit) - int(credit),
    )
