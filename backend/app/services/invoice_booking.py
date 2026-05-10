import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AccountLookupError, PeriodLockedError
from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.models.invoice import Invoice, InvoiceLineItem
from app.services.audit import write_audit
from app.services.booking import get_next_entry_number
from app.services.period import get_or_create_period


# SKR03: Debit = Forderungen aus LuL (1400), Credit = Umsatzerlöse
_VAT_ACCOUNTS_SKR03: dict[str, tuple[str, str]] = {
    "0.19": ("1400", "8400"),
    "0.07": ("1400", "8300"),
    "0.00": ("1400", "8200"),
}

# SKR04: Debit = Forderungen aus LuL (1200), Credit = Umsatzerlöse
_VAT_ACCOUNTS_SKR04: dict[str, tuple[str, str]] = {
    "0.19": ("1200", "4400"),
    "0.07": ("1200", "4300"),
    "0.00": ("1200", "4200"),
}


async def _get_account_id(
    session: AsyncSession, mandant_id: uuid.UUID, account_number: str
) -> uuid.UUID:
    """Look up a ChartOfAccount by account number for a mandant."""
    result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.account_number == account_number,
        )
    )
    coa = result.scalar_one_or_none()
    if coa is None:
        raise AccountLookupError(f"Account {account_number} not found for mandant.")
    return coa.id


async def create_issue_bookings(
    session: AsyncSession,
    invoice: Invoice,
    mandant_id: uuid.UUID,
    skr_variant: str,
    user_id: uuid.UUID,
) -> Booking:
    """Create posting-level Buchungssätze for an invoice being issued.

    Groups line items by VAT rate and creates one booking entry per VAT bucket.
    Returns the first (or only) booking created.
    """
    result = await session.execute(
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice.id)
        .order_by(InvoiceLineItem.position)
    )
    line_items = list(result.scalars().all())

    account_map = _VAT_ACCOUNTS_SKR04 if skr_variant == "skr04" else _VAT_ACCOUNTS_SKR03

    # Group gross amounts by VAT rate
    buckets: dict[str, int] = {}
    for item in line_items:
        key = f"{item.vat_rate:.2f}"
        gross = (item.net_total_cents or 0) + (item.vat_amount_cents or 0)
        buckets[key] = buckets.get(key, 0) + gross

    # Fix 2 (GoBD §14): Verify the target period is not locked or archived before
    # posting any booking.  Use invoice.issue_date as the authoritative period
    # reference — identical to how post_booking() guards direct postings.
    booking_date = invoice.issue_date or date.today()
    period = await get_or_create_period(
        session, mandant_id, booking_date.year, booking_date.month
    )
    if period.status in ("locked", "archived"):
        raise PeriodLockedError()

    first_booking: Booking | None = None
    for vat_key, gross_cents in buckets.items():
        if gross_cents == 0:
            continue
        debit_num, credit_num = account_map.get(vat_key, ("1400", "8400"))
        debit_id = await _get_account_id(session, mandant_id, debit_num)
        credit_id = await _get_account_id(session, mandant_id, credit_num)

        booking = Booking(
            mandant_id=mandant_id,
            booking_type="entry",
            date_booking=booking_date,
            amount_cents=gross_cents,
            currency=invoice.currency,
            document_number=invoice.invoice_number[:12],
            notes=f"RE {invoice.invoice_number}"[:60],
            coa_id=debit_id,
            counter_coa_id=credit_id,
            tax_rate=Decimal(vat_key),
            status="draft",
            invoice_id=invoice.id,
            created_by=user_id,
        )
        session.add(booking)
        await session.flush()

        entry_number = await get_next_entry_number(session, mandant_id)
        booking.status = "posted"
        booking.entry_number = entry_number

        # Fix 1 (GoBD §9): Record every draft→posted transition in the audit log,
        # matching the pattern used by post_booking() in booking.py.
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
        if first_booking is None:
            first_booking = booking

    if first_booking is None:
        raise AccountLookupError("Invoice has no billable line items.")

    await session.refresh(first_booking)
    return first_booking
