import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.models.user import User
from app.schemas.booking import (
    BookingCreate,
    BookingListResponse,
    BookingResponse,
    BookingUpdate,
)
from app.services.audit import list_booking_audit_log
from app.services.booking import (
    create_booking,
    delete_booking,
    get_booking,
    list_bookings,
    post_booking,
    reverse_booking,
    update_booking,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("", response_model=BookingListResponse)
async def list_(
    booking_type: Literal["bank", "entry"] | None = Query(None),
    status: Literal["draft", "posted", "reversed"] | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    account_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BookingListResponse:
    return await list_bookings(
        session,
        mandant_id,
        booking_type,
        status,
        date_from,
        date_to,
        account_id,
        page,
        page_size,
    )


@router.post("", response_model=BookingResponse, status_code=201)
async def create(
    body: BookingCreate,
    current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BookingResponse:
    return await create_booking(session, mandant_id, current_user.id, body)  # type: ignore[return-value]


@router.post("/{booking_id}/post", response_model=BookingResponse)
async def post(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BookingResponse:
    return await post_booking(session, booking_id, mandant_id, current_user.id)  # type: ignore[return-value]


@router.post("/{booking_id}/reverse", response_model=BookingResponse)
async def reverse(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BookingResponse:
    return await reverse_booking(session, booking_id, mandant_id, current_user.id)  # type: ignore[return-value]


@router.get("/{booking_id}/audit-log", response_model=list[dict[str, object]])
async def audit_log(
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    await get_booking(session, booking_id, mandant_id)
    return await list_booking_audit_log(session, booking_id, mandant_id)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get(
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BookingResponse:
    return await get_booking(session, booking_id, mandant_id)  # type: ignore[return-value]


@router.patch("/{booking_id}", response_model=BookingResponse)
async def update(
    booking_id: uuid.UUID,
    body: BookingUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BookingResponse:
    return await update_booking(session, booking_id, mandant_id, body)  # type: ignore[return-value]


@router.delete("/{booking_id}", status_code=204)
async def delete(
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> None:
    await delete_booking(session, booking_id, mandant_id)
