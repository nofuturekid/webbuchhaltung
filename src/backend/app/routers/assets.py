import uuid
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.errors import ConflictError
from app.models.asset import DepreciationSchedule
from app.models.user import User
from app.schemas.asset import (
    AssetCreate,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
    BookDepreciationRequest,
    DepreciationScheduleEntry,
    DisposeAssetRequest,
)
from app.services.asset import (
    book_depreciation,
    create_asset,
    dispose_asset,
    get_asset,
    get_depreciation_schedule,
    list_assets,
    update_asset,
)

router = APIRouter(prefix="/assets", tags=["assets"])


async def _compute_nbv(
    session: AsyncSession, asset_id: uuid.UUID, purchase_amount_cents: int
) -> tuple[int, int]:
    """Return (total_depreciated_cents, net_book_value_cents) from the last posted schedule row."""
    last_posted = (
        await session.execute(
            select(DepreciationSchedule)
            .where(
                DepreciationSchedule.asset_id == asset_id,
                DepreciationSchedule.booking_id.is_not(None),
            )
            .order_by(
                DepreciationSchedule.period_year.desc(),
                DepreciationSchedule.period_month.desc(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if last_posted is not None:
        return (
            last_posted.cumulative_depreciation_cents,
            last_posted.net_book_value_cents,
        )
    return 0, purchase_amount_cents


@router.get("/", response_model=AssetListResponse, summary="List assets")
async def list_assets_endpoint(
    page: int = 1,
    page_size: int = 50,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> AssetListResponse:
    return await list_assets(session, mandant_id, page, page_size)


@router.post(
    "/",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create asset",
)
async def create_asset_endpoint(
    payload: AssetCreate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AssetResponse:
    asset = await create_asset(session, mandant_id, current_user.id, payload)
    resp = AssetResponse.model_validate(asset)
    resp.total_depreciated_cents = 0
    resp.net_book_value_cents = asset.purchase_amount_cents
    return resp


@router.get("/{asset_id}", response_model=AssetResponse, summary="Get asset")
async def get_asset_endpoint(
    asset_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> AssetResponse:
    asset = await get_asset(session, asset_id, mandant_id)
    resp = AssetResponse.model_validate(asset)
    resp.total_depreciated_cents, resp.net_book_value_cents = await _compute_nbv(
        session, asset.id, asset.purchase_amount_cents
    )
    return resp


@router.patch("/{asset_id}", response_model=AssetResponse, summary="Update asset")
async def update_asset_endpoint(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AssetResponse:
    asset = await update_asset(session, asset_id, mandant_id, current_user.id, payload)
    resp = AssetResponse.model_validate(asset)
    resp.total_depreciated_cents, resp.net_book_value_cents = await _compute_nbv(
        session, asset.id, asset.purchase_amount_cents
    )
    return resp


@router.delete(
    "/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete asset"
)
async def delete_asset_endpoint(
    asset_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> None:
    asset = await get_asset(session, asset_id, mandant_id)

    posted_check = (
        await session.execute(
            select(DepreciationSchedule)
            .where(
                DepreciationSchedule.asset_id == asset.id,
                DepreciationSchedule.booking_id.is_not(None),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if posted_check is not None:
        raise ConflictError(
            "Cannot delete an asset with posted depreciation bookings (GoBD)."
        )

    await session.delete(asset)
    await session.flush()


@router.get(
    "/{asset_id}/depreciation-schedule",
    response_model=list[DepreciationScheduleEntry],
    summary="Get depreciation schedule",
)
async def get_depreciation_schedule_endpoint(
    asset_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list[DepreciationSchedule]:
    return await get_depreciation_schedule(session, asset_id, mandant_id)


@router.post("/{asset_id}/book-depreciation", summary="Book depreciation for a period")
async def book_depreciation_endpoint(
    asset_id: uuid.UUID,
    payload: BookDepreciationRequest,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    today = date.today()
    period_year = payload.period_year if payload.period_year is not None else today.year
    period_month = (
        payload.period_month if payload.period_month is not None else today.month
    )

    booking = await book_depreciation(
        session, asset_id, mandant_id, current_user.id, period_year, period_month
    )
    return {
        "booking_id": str(booking.id),
        "entry_number": booking.entry_number,
        "period_year": period_year,
        "period_month": period_month,
        "amount_cents": booking.amount_cents,
    }


@router.post(
    "/{asset_id}/dispose", response_model=AssetResponse, summary="Dispose asset"
)
async def dispose_asset_endpoint(
    asset_id: uuid.UUID,
    payload: DisposeAssetRequest,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AssetResponse:
    asset = await dispose_asset(session, asset_id, mandant_id, current_user.id, payload)
    resp = AssetResponse.model_validate(asset)
    resp.total_depreciated_cents, resp.net_book_value_cents = await _compute_nbv(
        session, asset.id, asset.purchase_amount_cents
    )
    return resp
