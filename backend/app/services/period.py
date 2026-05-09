import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
