import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import BookingAlreadyPostedError, NotFoundError
from app.models.booking import Booking
from app.schemas.booking import BookingCreate, BookingListResponse, BookingUpdate


async def get_booking(
    session: AsyncSession, booking_id: uuid.UUID, mandant_id: uuid.UUID
) -> Booking:
    result = await session.execute(
        select(Booking).where(
            Booking.id == booking_id, Booking.mandant_id == mandant_id
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise NotFoundError(f"Booking {booking_id} not found.")
    return booking


async def list_bookings(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    booking_type: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 50,
) -> BookingListResponse:
    q = select(Booking).where(Booking.mandant_id == mandant_id)
    if booking_type:
        q = q.where(Booking.booking_type == booking_type)
    if status:
        q = q.where(Booking.status == status)
    if date_from:
        q = q.where(Booking.date_booking >= date_from)
    if date_to:
        q = q.where(Booking.date_booking <= date_to)
    if account_id:
        q = q.where(
            (Booking.coa_id == account_id) | (Booking.counter_coa_id == account_id)
        )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(count_q)).scalar_one()
    items_result = await session.execute(
        q.order_by(Booking.date_booking.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(items_result.scalars().all())
    return BookingListResponse(
        items=items, total=int(total), page=page, page_size=page_size
    )


async def create_booking(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: BookingCreate,
) -> Booking:
    booking = Booking(
        mandant_id=mandant_id,
        created_by=user_id,
        **data.model_dump(),
    )
    session.add(booking)
    await session.flush()
    await session.refresh(booking)
    return booking


async def update_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID,
    data: BookingUpdate,
) -> Booking:
    booking = await get_booking(session, booking_id, mandant_id)
    if booking.status == "posted":
        raise BookingAlreadyPostedError()
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(booking, field, value)
    await session.flush()
    await session.refresh(booking)
    return booking


async def delete_booking(
    session: AsyncSession, booking_id: uuid.UUID, mandant_id: uuid.UUID
) -> None:
    booking = await get_booking(session, booking_id, mandant_id)
    if booking.status != "draft":
        raise BookingAlreadyPostedError()
    await session.delete(booking)
    await session.flush()
