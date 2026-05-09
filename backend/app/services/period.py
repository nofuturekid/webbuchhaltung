import uuid

from sqlalchemy import select
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
    if not period:
        period = AccountingPeriod(
            mandant_id=mandant_id, year=year, month=month, status="open"
        )
        session.add(period)
        await session.flush()
    return period
