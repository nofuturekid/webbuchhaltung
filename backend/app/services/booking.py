import uuid
from datetime import date

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import (
    BookingAlreadyPostedError,
    ConflictError,
    NotFoundError,
    PeriodLockedError,
)
from app.models.booking import Booking
from app.schemas.booking import BookingCreate, BookingListResponse, BookingUpdate
from app.services.audit import write_audit
from app.services.period import get_or_create_period


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
    if booking.status != "draft":
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


async def get_next_entry_number(session: AsyncSession, mandant_id: uuid.UUID) -> int:
    conn = await session.connection()
    dialect_name = conn.dialect.name
    if dialect_name == "postgresql":
        result = await session.execute(
            text(
                "INSERT INTO booking_sequences (mandant_id, next_value) VALUES (:id, 2) "
                "ON CONFLICT (mandant_id) DO UPDATE "
                "SET next_value = booking_sequences.next_value + 1 "
                "RETURNING next_value - 1"
            ),
            {"id": str(mandant_id)},
        )
        return int(result.scalar_one())
    elif dialect_name in ("mysql", "mariadb"):
        # LAST_INSERT_ID(expr) sets the connection-scoped value atomically
        await session.execute(
            text(
                "INSERT INTO booking_sequences (mandant_id, next_value) "
                "VALUES (:id, LAST_INSERT_ID(1)) "
                "ON DUPLICATE KEY UPDATE next_value = LAST_INSERT_ID(next_value + 1)"
            ),
            {"id": str(mandant_id)},
        )
        result = await session.execute(text("SELECT LAST_INSERT_ID()"))
        return int(result.scalar_one())
    else:
        raise NotImplementedError(
            f"Unsupported dialect for entry number sequencing: {dialect_name}"
        )


async def post_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Booking:
    booking = await get_booking(session, booking_id, mandant_id)
    if booking.status != "draft":
        raise BookingAlreadyPostedError()

    period = await get_or_create_period(
        session, mandant_id, booking.date_booking.year, booking.date_booking.month
    )
    if period.status in ("locked", "archived"):
        raise PeriodLockedError()

    entry_number = await get_next_entry_number(session, mandant_id)
    booking.status = "posted"
    booking.entry_number = entry_number

    await write_audit(
        session,
        table_name="bookings",
        record_id=booking.id,
        action="update",
        change_summary={
            "transition": "draft→posted",
            "status": ["draft", "posted"],
            "entry_number": [None, entry_number],
        },
        mandant_id=mandant_id,
        user_id=user_id,
    )
    await session.flush()
    await session.refresh(booking)
    return booking


async def reverse_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Booking:
    original = await get_booking(session, booking_id, mandant_id)
    if original.status != "posted":
        raise ConflictError("Only posted bookings can be reversed.")
    if original.reversal_of_id is not None:
        raise ConflictError("A reversal booking cannot itself be reversed.")

    period = await get_or_create_period(
        session, mandant_id, original.date_booking.year, original.date_booking.month
    )
    if period.status in ("locked", "archived"):
        raise PeriodLockedError()

    _prefix = "STORNO: "
    _max_orig = 60 - len(_prefix)
    reversal = Booking(
        mandant_id=mandant_id,
        booking_type=original.booking_type,
        date_booking=original.date_booking,
        date_tax=original.date_tax,
        amount_cents=original.amount_cents,
        currency=original.currency,
        document_number=original.document_number,
        notes=f"{_prefix}{(original.notes or '')[:_max_orig]}",
        coa_id=original.counter_coa_id,
        counter_coa_id=original.coa_id,
        tax_rate=original.tax_rate,
        tax_amount_cents=original.tax_amount_cents,
        tax_key_code=original.tax_key_code,
        reversal_of_id=original.id,
        created_by=user_id,
    )
    session.add(reversal)
    await session.flush()

    reversal_number = await get_next_entry_number(session, mandant_id)
    reversal.status = "posted"
    reversal.entry_number = reversal_number
    original.status = "reversed"

    await write_audit(
        session,
        "bookings",
        original.id,
        "update",
        {"status": ["posted", "reversed"]},
        mandant_id,
        user_id,
    )
    await write_audit(
        session,
        "bookings",
        reversal.id,
        "insert",
        {"reversal_of": str(original.id), "entry_number": reversal_number},
        mandant_id,
        user_id,
    )
    await session.flush()
    await session.refresh(reversal)
    return reversal
