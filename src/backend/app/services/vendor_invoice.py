import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import (
    ConflictError,
    NotFoundError,
    PeriodLockedError,
    VendorInvoiceImmutableError,
)
from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.models.vendor import Vendor, VendorInvoice
from app.schemas.vendor import (
    VendorCreate,
    VendorInvoiceCreate,
    VendorInvoiceListResponse,
    VendorInvoiceResponse,
    VendorListResponse,
    VendorResponse,
    VendorUpdate,
)
from app.services.audit import write_audit
from app.services.booking import get_next_entry_number
from app.services.period import get_or_create_period


# AP account numbers by SKR variant (Verbindlichkeiten aus LuL)
_AP_ACCOUNT: dict[str, str] = {
    "skr03": "1600",
    "skr04": "3300",
    "skr07": "1600",  # default to skr03 pattern for skr07
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
        raise ConflictError(f"Account {account_number} not found for mandant.")
    return coa.id


# ---------------------------------------------------------------------------
# Vendor CRUD
# ---------------------------------------------------------------------------


async def create_vendor(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: VendorCreate,
) -> Vendor:
    vendor = Vendor(
        mandant_id=mandant_id,
        **data.model_dump(),
    )
    session.add(vendor)
    await session.flush()
    await session.refresh(vendor)
    return vendor


async def list_vendors(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> VendorListResponse:
    q = select(Vendor).where(Vendor.mandant_id == mandant_id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(count_q)).scalar_one()
    items_result = await session.execute(
        q.order_by(Vendor.name).offset((page - 1) * page_size).limit(page_size)
    )
    items = list(items_result.scalars().all())
    return VendorListResponse(
        items=[VendorResponse.model_validate(v) for v in items],
        total=int(total),
        page=page,
        page_size=page_size,
    )


async def get_vendor(
    session: AsyncSession, vendor_id: uuid.UUID, mandant_id: uuid.UUID
) -> Vendor:
    result = await session.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.mandant_id == mandant_id)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise NotFoundError(f"Vendor {vendor_id} not found.")
    return vendor


async def update_vendor(
    session: AsyncSession,
    vendor_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: VendorUpdate,
) -> Vendor:
    vendor = await get_vendor(session, vendor_id, mandant_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)
    await session.flush()
    await session.refresh(vendor)
    return vendor


# ---------------------------------------------------------------------------
# Vendor Invoice CRUD
# ---------------------------------------------------------------------------


async def create_vendor_invoice(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: VendorInvoiceCreate,
) -> VendorInvoice:
    # Verify vendor belongs to mandant
    await get_vendor(session, data.vendor_id, mandant_id)

    invoice = VendorInvoice(
        mandant_id=mandant_id,
        created_by=user_id,
        **data.model_dump(),
    )
    session.add(invoice)
    await session.flush()
    await session.refresh(invoice)
    return invoice


async def list_vendor_invoices(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    vendor_id: uuid.UUID | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
) -> VendorInvoiceListResponse:
    q = select(VendorInvoice).where(VendorInvoice.mandant_id == mandant_id)
    if status:
        q = q.where(VendorInvoice.status == status)
    if vendor_id:
        q = q.where(VendorInvoice.vendor_id == vendor_id)
    if due_from:
        q = q.where(VendorInvoice.due_date >= due_from)
    if due_to:
        q = q.where(VendorInvoice.due_date <= due_to)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(count_q)).scalar_one()
    items_result = await session.execute(
        q.order_by(VendorInvoice.invoice_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(items_result.scalars().all())
    return VendorInvoiceListResponse(
        items=[VendorInvoiceResponse.model_validate(i) for i in items],
        total=int(total),
        page=page,
        page_size=page_size,
    )


async def get_vendor_invoice(
    session: AsyncSession, invoice_id: uuid.UUID, mandant_id: uuid.UUID
) -> VendorInvoice:
    result = await session.execute(
        select(VendorInvoice).where(
            VendorInvoice.id == invoice_id,
            VendorInvoice.mandant_id == mandant_id,
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise NotFoundError(f"Vendor invoice {invoice_id} not found.")
    return invoice


# ---------------------------------------------------------------------------
# Vendor Invoice state transitions
# ---------------------------------------------------------------------------


async def post_vendor_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    expense_coa_id: uuid.UUID,
    skr_variant: str,
) -> VendorInvoice:
    """GoBD-compliant posting of a vendor invoice (Eingangsrechnung).

    Creates a double-entry booking:
      SOLL  — expense_coa_id (chosen by user, e.g. office supplies)
      HABEN — AP account (1600 SKR03 / 3300 SKR04)
    """
    invoice = await get_vendor_invoice(session, invoice_id, mandant_id)

    if invoice.status != "draft":
        raise VendorInvoiceImmutableError()

    period = await get_or_create_period(
        session,
        mandant_id,
        invoice.invoice_date.year,
        invoice.invoice_date.month,
    )
    if period.status in ("locked", "archived"):
        raise PeriodLockedError()

    entry_number = await get_next_entry_number(session, mandant_id)

    # Resolve AP account number for the SKR variant
    ap_account_number = _AP_ACCOUNT.get(skr_variant, "1600")
    ap_account_id = await _get_account_id(session, mandant_id, ap_account_number)

    booking = Booking(
        mandant_id=mandant_id,
        booking_type="entry",
        date_booking=invoice.invoice_date,
        amount_cents=invoice.amount_cents,
        currency=invoice.currency,
        document_number=invoice.invoice_number[:12],
        notes=f"Eingangsrechnung {invoice.invoice_number}"[:60],
        coa_id=expense_coa_id,  # SOLL — expense account
        counter_coa_id=ap_account_id,  # HABEN — AP account
        status="draft",
        created_by=user_id,
    )
    session.add(booking)
    await session.flush()

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

    invoice.status = "posted"
    invoice.booking_id = booking.id

    await write_audit(
        session,
        table_name="vendor_invoices",
        record_id=invoice.id,
        action="update",
        change_summary={
            "transition": "draft→posted",
            "status": ["draft", "posted"],
            "booking_id": [None, str(booking.id)],
        },
        mandant_id=mandant_id,
        user_id=user_id,
    )

    await session.flush()
    await session.refresh(invoice)
    return invoice


async def mark_vendor_invoice_paid(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> VendorInvoice:
    """Transition a posted vendor invoice to paid status."""
    invoice = await get_vendor_invoice(session, invoice_id, mandant_id)

    if invoice.status != "posted":
        raise ConflictError(
            f"Only posted invoices can be marked paid. Current status: {invoice.status}"
        )

    invoice.status = "paid"

    await write_audit(
        session,
        table_name="vendor_invoices",
        record_id=invoice.id,
        action="update",
        change_summary={"transition": "posted→paid", "status": ["posted", "paid"]},
        mandant_id=mandant_id,
        user_id=user_id,
    )

    await session.flush()
    await session.refresh(invoice)
    return invoice


async def cancel_vendor_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> VendorInvoice:
    """Cancel a draft vendor invoice.

    GoBD: Only draft invoices can be cancelled. Posted invoices are immutable —
    they must be reversed via a corrective booking instead.
    Paid invoices cannot be cancelled either.
    """
    invoice = await get_vendor_invoice(session, invoice_id, mandant_id)

    if invoice.status == "posted":
        raise VendorInvoiceImmutableError()

    if invoice.status != "draft":
        raise ConflictError(
            f"Only draft invoices can be cancelled. Current status: {invoice.status}"
        )

    invoice.status = "cancelled"

    await write_audit(
        session,
        table_name="vendor_invoices",
        record_id=invoice.id,
        action="update",
        change_summary={
            "transition": "draft→cancelled",
            "status": ["draft", "cancelled"],
        },
        mandant_id=mandant_id,
        user_id=user_id,
    )

    await session.flush()
    await session.refresh(invoice)
    return invoice
