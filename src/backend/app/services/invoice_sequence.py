import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import InvoiceSequence


async def allocate_invoice_number(session: AsyncSession, mandant_id: uuid.UUID) -> str:
    """Allocate the next sequential invoice number for a mandant.

    Uses a row-level lock (SELECT ... FOR UPDATE) to prevent concurrent duplicates.
    Resets numbering annually if year_reset is enabled.
    """
    result = await session.execute(
        select(InvoiceSequence)
        .where(InvoiceSequence.mandant_id == mandant_id)
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = InvoiceSequence(mandant_id=mandant_id)
        session.add(seq)
        await session.flush()

    current_year = date.today().year

    if seq.year_reset and seq.last_reset_year != current_year:
        seq.next_number = 1
        seq.last_reset_year = current_year

    number = seq.next_number
    seq.next_number += 1

    if seq.year_reset:
        invoice_number = f"{seq.prefix}-{current_year}-{number:03d}"
    else:
        invoice_number = f"{seq.prefix}-{number:03d}"

    await session.flush()
    return invoice_number


async def get_or_create_sequence(
    session: AsyncSession, mandant_id: uuid.UUID
) -> InvoiceSequence:
    """Return the InvoiceSequence for the given mandant, creating it if absent."""
    result = await session.execute(
        select(InvoiceSequence).where(InvoiceSequence.mandant_id == mandant_id)
    )
    seq = result.scalar_one_or_none()
    if seq is None:
        seq = InvoiceSequence(mandant_id=mandant_id)
        session.add(seq)
        await session.flush()
        await session.refresh(seq)
    return seq


async def update_sequence(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    prefix: str | None,
    year_reset: bool | None,
) -> InvoiceSequence:
    """Update sequence settings (prefix and/or year_reset flag)."""
    seq = await get_or_create_sequence(session, mandant_id)
    if prefix is not None:
        seq.prefix = prefix
    if year_reset is not None:
        seq.year_reset = year_reset
    await session.flush()
    await session.refresh(seq)
    return seq
