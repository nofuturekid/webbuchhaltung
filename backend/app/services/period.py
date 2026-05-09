import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError
from app.models.period import AccountingPeriod


async def get_or_create_period(
    session: AsyncSession, mandant_id: uuid.UUID, year: int, month: int
) -> AccountingPeriod:
    result = await session.execute(
        select(AccountingPeriod).where(
            AccountingPeriod.mandant_id == mandant_id,
            AccountingPeriod.year == year,
            AccountingPeriod.month == month,
        )
    )
    period = result.scalar_one_or_none()
    if period:
        return period
    try:
        async with session.begin_nested():
            period = AccountingPeriod(
                mandant_id=mandant_id, year=year, month=month, status="open"
            )
            session.add(period)
    except IntegrityError:
        # Concurrent request created the period — re-query
        result = await session.execute(
            select(AccountingPeriod).where(
                AccountingPeriod.mandant_id == mandant_id,
                AccountingPeriod.year == year,
                AccountingPeriod.month == month,
            )
        )
        period = result.scalar_one()
    return period


async def list_periods(
    session: AsyncSession, mandant_id: uuid.UUID
) -> list[AccountingPeriod]:
    result = await session.execute(
        select(AccountingPeriod)
        .where(AccountingPeriod.mandant_id == mandant_id)
        .order_by(AccountingPeriod.year, AccountingPeriod.month)
    )
    return list(result.scalars().all())


async def lock_period(
    session: AsyncSession, period_id: uuid.UUID, mandant_id: uuid.UUID
) -> AccountingPeriod:
    result = await session.execute(
        select(AccountingPeriod).where(
            AccountingPeriod.id == period_id,
            AccountingPeriod.mandant_id == mandant_id,
        )
    )
    period = result.scalar_one_or_none()
    if not period:
        raise NotFoundError(f"Period {period_id} not found.")
    if period.status != "open":
        raise ConflictError("Only open periods can be locked.")
    period.status = "locked"
    period.locked_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(period)
    return period


async def archive_period(
    session: AsyncSession, period_id: uuid.UUID, mandant_id: uuid.UUID
) -> AccountingPeriod:
    result = await session.execute(
        select(AccountingPeriod).where(
            AccountingPeriod.id == period_id,
            AccountingPeriod.mandant_id == mandant_id,
        )
    )
    period = result.scalar_one_or_none()
    if not period:
        raise NotFoundError(f"Period {period_id} not found.")
    if period.status != "locked":
        raise ConflictError("Only locked periods can be archived.")
    period.status = "archived"
    await session.flush()
    await session.refresh(period)
    return period
