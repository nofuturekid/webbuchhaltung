import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.models.user import User
from app.schemas.period import PeriodResponse
from app.services.period import archive_period, list_periods, lock_period

router = APIRouter(prefix="/periods", tags=["periods"])


@router.get("", response_model=list[PeriodResponse])
async def list_(
    _current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list[PeriodResponse]:
    return await list_periods(session, mandant_id)  # type: ignore[return-value]


@router.post("/{period_id}/lock", response_model=PeriodResponse)
async def lock(
    period_id: uuid.UUID,
    _current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> PeriodResponse:
    return await lock_period(session, period_id, mandant_id)  # type: ignore[return-value]


@router.post("/{period_id}/archive", response_model=PeriodResponse)
async def archive(
    period_id: uuid.UUID,
    _current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> PeriodResponse:
    return await archive_period(session, period_id, mandant_id)  # type: ignore[return-value]
