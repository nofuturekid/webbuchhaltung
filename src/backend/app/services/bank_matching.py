import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import BankTransactionAlreadyMatchedError, ConflictError, NotFoundError
from app.models.bank import BankTransaction
from app.models.booking import Booking
from app.services.audit import write_audit


@dataclass
class MatchCandidate:
    booking_id: uuid.UUID
    booking_date: date
    amount_cents: int
    description: str | None
    entry_number: int
    score: float


async def find_match_candidates(
    session: AsyncSession,
    transaction_id: uuid.UUID,
    mandant_id: uuid.UUID,
    date_window_days: int = 7,
) -> list[MatchCandidate]:
    """Return ranked candidate bookings for an unmatched bank transaction.

    Scoring:
    - amount exact match: +0.60
    - date within ±3 days: +0.30; within ±7 days: +0.15
    - purpose contains entry_number: +0.10
    """
    tx = await _get_transaction(session, transaction_id, mandant_id)

    window_start = tx.transaction_date - timedelta(days=date_window_days)
    window_end = tx.transaction_date + timedelta(days=date_window_days)

    bookings = (
        (
            await session.execute(
                select(Booking).where(
                    Booking.mandant_id == mandant_id,
                    Booking.status == "posted",
                    Booking.bank_account_id.is_(None),
                    Booking.date_booking >= window_start,
                    Booking.date_booking <= window_end,
                )
            )
        )
        .scalars()
        .all()
    )

    candidates: list[MatchCandidate] = []
    for b in bookings:
        score = 0.0
        if b.amount_cents == abs(tx.amount_cents):
            score += 0.60
        days_diff = abs((b.date_booking - tx.transaction_date).days)
        if days_diff <= 3:
            score += 0.30
        elif days_diff <= 7:
            score += 0.15
        if (
            tx.purpose
            and b.entry_number is not None
            and str(b.entry_number) in tx.purpose
        ):
            score += 0.10
        if score > 0:
            candidates.append(
                MatchCandidate(
                    booking_id=b.id,
                    booking_date=b.date_booking,
                    amount_cents=b.amount_cents,
                    description=b.notes,
                    entry_number=b.entry_number,  # type: ignore[arg-type]
                    score=score,
                )
            )

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


async def apply_match(
    session: AsyncSession,
    transaction_id: uuid.UUID,
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Link a bank transaction to a booking."""
    tx = await _get_transaction(session, transaction_id, mandant_id)
    if tx.status == "matched":
        raise BankTransactionAlreadyMatchedError()

    booking = (
        await session.execute(
            select(Booking).where(
                Booking.id == booking_id, Booking.mandant_id == mandant_id
            )
        )
    ).scalar_one_or_none()
    if booking is None:
        raise NotFoundError(f"Booking {booking_id} not found.")

    tx.status = "matched"
    tx.booking_id = booking_id
    booking.bank_account_id = tx.bank_account_id
    await session.flush()
    await write_audit(
        session,
        table_name="bookings",
        record_id=booking_id,
        action="update",
        change_summary={"bank_match": str(transaction_id)},
        mandant_id=mandant_id,
        user_id=user_id,
    )


async def apply_ignore(
    session: AsyncSession,
    transaction_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> BankTransaction:
    """Mark a bank transaction as ignored (no matching booking needed)."""
    tx = await _get_transaction(session, transaction_id, mandant_id)
    tx.status = "ignored"
    await session.flush()
    await write_audit(
        session,
        table_name="bank_transactions",
        record_id=transaction_id,
        action="update",
        change_summary={"status": ["unmatched", "ignored"]},
        mandant_id=mandant_id,
        user_id=user_id,
    )
    return tx


async def apply_unmatch(
    session: AsyncSession,
    transaction_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> BankTransaction:
    """Remove the link between a bank transaction and a booking."""
    tx = await _get_transaction(session, transaction_id, mandant_id)
    if tx.status != "matched":
        raise ConflictError("Transaction is not matched.")
    prior_booking_id = tx.booking_id
    if prior_booking_id:
        booking = (
            await session.execute(select(Booking).where(Booking.id == prior_booking_id))
        ).scalar_one_or_none()
        if booking:
            booking.bank_account_id = None
    tx.status = "unmatched"
    tx.booking_id = None
    await session.flush()
    if prior_booking_id:
        await write_audit(
            session,
            table_name="bookings",
            record_id=prior_booking_id,
            action="update",
            change_summary={"bank_unmatch": str(transaction_id)},
            mandant_id=mandant_id,
            user_id=user_id,
        )
    await write_audit(
        session,
        table_name="bank_transactions",
        record_id=transaction_id,
        action="update",
        change_summary={
            "status": ["matched", "unmatched"],
            "booking_id": str(prior_booking_id),
        },
        mandant_id=mandant_id,
        user_id=user_id,
    )
    return tx


async def run_auto_matching(
    session: AsyncSession,
    bank_account_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[int, int]:
    """Run automatic matching for all unmatched transactions.

    Auto-applies matches where best candidate score >= 0.90.
    Returns (auto_matched_count, remaining_unmatched_count).
    """
    unmatched = (
        (
            await session.execute(
                select(BankTransaction).where(
                    BankTransaction.bank_account_id == bank_account_id,
                    BankTransaction.mandant_id == mandant_id,
                    BankTransaction.status == "unmatched",
                )
            )
        )
        .scalars()
        .all()
    )

    matched_count = 0
    for tx in unmatched:
        candidates = await find_match_candidates(session, tx.id, mandant_id)
        if candidates and candidates[0].score >= 0.90:
            await apply_match(
                session, tx.id, candidates[0].booking_id, mandant_id, user_id
            )
            matched_count += 1

    remaining = (
        (
            await session.execute(
                select(BankTransaction).where(
                    BankTransaction.bank_account_id == bank_account_id,
                    BankTransaction.status == "unmatched",
                )
            )
        )
        .scalars()
        .all()
    )

    return matched_count, len(remaining)


async def _get_transaction(
    session: AsyncSession, tx_id: uuid.UUID, mandant_id: uuid.UUID
) -> BankTransaction:
    tx = (
        await session.execute(
            select(BankTransaction).where(
                BankTransaction.id == tx_id,
                BankTransaction.mandant_id == mandant_id,
            )
        )
    ).scalar_one_or_none()
    if tx is None:
        raise NotFoundError(f"Bank transaction {tx_id} not found.")
    return tx
