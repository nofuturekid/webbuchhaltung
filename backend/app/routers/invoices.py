import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.errors import InvoiceImmutableError, InvalidInvoiceStateError, NotFoundError
from app.models.invoice import Customer, Invoice, InvoiceLineItem, InvoiceTemplate
from app.models.mandant import Mandant
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListItem,
    InvoiceResponse,
    InvoiceUpdate,
    LineItemResponse,
    SendEmailRequest,
)
from app.services.booking import reverse_booking
from app.services.invoice_booking import create_issue_bookings
from app.services.invoice_email import send_invoice_email
from app.services.invoice_pdf import render_invoice_pdf
from app.services.invoice_sequence import allocate_invoice_number

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _compute_line_item_totals(item: InvoiceLineItem) -> None:
    """Compute and set net_total_cents and vat_amount_cents on a line item."""
    net = int(Decimal(str(item.quantity)) * item.unit_price_cents)
    vat = int(net * item.vat_rate)
    item.net_total_cents = net
    item.vat_amount_cents = vat


def _compute_invoice_totals(
    invoice: Invoice, line_items: list[InvoiceLineItem]
) -> None:
    """Aggregate line item totals into invoice-level totals."""
    net = sum(i.net_total_cents or 0 for i in line_items)
    vat = sum(i.vat_amount_cents or 0 for i in line_items)
    invoice.net_total_cents = net
    invoice.vat_total_cents = vat
    invoice.gross_total_cents = net + vat


async def _get_invoice(
    session: AsyncSession, invoice_id: uuid.UUID, mandant_id: uuid.UUID
) -> Invoice:
    result = await session.execute(
        select(Invoice).where(
            Invoice.id == invoice_id, Invoice.mandant_id == mandant_id
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise NotFoundError(f"Invoice {invoice_id} not found.")
    return inv


async def _get_line_items(
    session: AsyncSession, invoice_id: uuid.UUID
) -> list[InvoiceLineItem]:
    result = await session.execute(
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice_id)
        .order_by(InvoiceLineItem.position)
    )
    return list(result.scalars().all())


async def _build_response(session: AsyncSession, invoice: Invoice) -> InvoiceResponse:
    line_items = await _get_line_items(session, invoice.id)
    data = InvoiceResponse.model_validate(invoice)
    data.line_items = [LineItemResponse.model_validate(li) for li in line_items]
    return data


@router.get("/", response_model=list[InvoiceListItem])
async def list_invoices(
    status_filter: str | None = None,
    customer_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list[Invoice]:
    q = select(Invoice).where(Invoice.mandant_id == mandant_id)
    if status_filter:
        q = q.where(Invoice.status == status_filter)
    if customer_id:
        q = q.where(Invoice.customer_id == customer_id)
    if date_from:
        q = q.where(Invoice.issue_date >= date_from)
    if date_to:
        q = q.where(Invoice.issue_date <= date_to)
    q = q.order_by(Invoice.created_at.desc())
    result = await session.execute(q)
    return list(result.scalars().all())


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    invoice_number = await allocate_invoice_number(session, mandant_id)
    invoice = Invoice(
        mandant_id=mandant_id,
        customer_id=payload.customer_id,
        invoice_number=invoice_number,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        notes=payload.notes,
    )
    session.add(invoice)
    await session.flush()

    line_items: list[InvoiceLineItem] = []
    for li_data in payload.line_items:
        li = InvoiceLineItem(invoice_id=invoice.id, **li_data.model_dump())
        _compute_line_item_totals(li)
        session.add(li)
        line_items.append(li)
    await session.flush()

    _compute_invoice_totals(invoice, line_items)
    await session.flush()
    await session.refresh(invoice)
    return await _build_response(session, invoice)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    invoice = await _get_invoice(session, invoice_id, mandant_id)
    return await _build_response(session, invoice)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    invoice = await _get_invoice(session, invoice_id, mandant_id)
    if invoice.status != "draft":
        raise InvoiceImmutableError()

    for field in ("customer_id", "issue_date", "due_date", "notes"):
        value = getattr(payload, field, None)
        if value is not None:
            setattr(invoice, field, value)

    if payload.line_items is not None:
        existing = await session.execute(
            select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice_id)
        )
        for old in existing.scalars().all():
            await session.delete(old)
        await session.flush()

        new_items: list[InvoiceLineItem] = []
        for li_data in payload.line_items:
            li = InvoiceLineItem(invoice_id=invoice.id, **li_data.model_dump())
            _compute_line_item_totals(li)
            session.add(li)
            new_items.append(li)
        await session.flush()
        _compute_invoice_totals(invoice, new_items)

    await session.flush()
    await session.refresh(invoice)
    return await _build_response(session, invoice)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> None:
    invoice = await _get_invoice(session, invoice_id, mandant_id)
    if invoice.status != "draft":
        raise InvoiceImmutableError()
    line_items = await _get_line_items(session, invoice_id)
    for li in line_items:
        await session.delete(li)
    await session.flush()
    await session.delete(invoice)
    await session.flush()


@router.post("/{invoice_id}/issue", response_model=InvoiceResponse)
async def issue_invoice(
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    invoice = await _get_invoice(session, invoice_id, mandant_id)
    if invoice.status != "draft":
        raise InvalidInvoiceStateError(
            f"Cannot issue invoice with status '{invoice.status}'."
        )

    mandant_result = await session.execute(
        select(Mandant).where(Mandant.id == mandant_id)
    )
    mandant = mandant_result.scalar_one()

    if invoice.issue_date is None:
        invoice.issue_date = date.today()

    booking = await create_issue_bookings(
        session, invoice, mandant_id, mandant.skr_variant, current_user.id
    )
    invoice.booking_id = booking.id
    invoice.status = "issued"

    await session.flush()
    await session.refresh(invoice)
    return await _build_response(session, invoice)


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    invoice = await _get_invoice(session, invoice_id, mandant_id)
    if invoice.status != "issued":
        raise InvalidInvoiceStateError(
            f"Cannot cancel invoice with status '{invoice.status}'."
        )

    if invoice.booking_id:
        await reverse_booking(session, invoice.booking_id, mandant_id, current_user.id)

    invoice.status = "cancelled"
    await session.flush()
    await session.refresh(invoice)
    return await _build_response(session, invoice)


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> Response:
    invoice = await _get_invoice(session, invoice_id, mandant_id)
    line_items = await _get_line_items(session, invoice_id)

    mandant_result = await session.execute(
        select(Mandant).where(Mandant.id == mandant_id)
    )
    mandant = mandant_result.scalar_one()

    customer_result = await session.execute(
        select(Customer).where(Customer.id == invoice.customer_id)
    )
    customer = customer_result.scalar_one()

    tmpl_result = await session.execute(
        select(InvoiceTemplate).where(InvoiceTemplate.mandant_id == mandant_id)
    )
    tmpl = tmpl_result.scalar_one_or_none()
    if tmpl is None:
        tmpl = InvoiceTemplate(mandant_id=mandant_id)

    li_dicts = [
        {
            "position": li.position,
            "description": li.description,
            "quantity": float(li.quantity),
            "unit": li.unit,
            "unit_price_cents": li.unit_price_cents,
            "vat_rate": float(li.vat_rate),
            "net_total_cents": li.net_total_cents,
            "vat_amount_cents": li.vat_amount_cents,
        }
        for li in line_items
    ]

    pdf_bytes = render_invoice_pdf(invoice, mandant, customer, li_dicts, tmpl)
    filename = f"{invoice.invoice_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{invoice_id}/send-email")
async def send_invoice_email_endpoint(
    invoice_id: uuid.UUID,
    payload: SendEmailRequest,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> dict:
    invoice = await _get_invoice(session, invoice_id, mandant_id)
    line_items = await _get_line_items(session, invoice_id)

    mandant_result = await session.execute(
        select(Mandant).where(Mandant.id == mandant_id)
    )
    mandant = mandant_result.scalar_one()

    customer_result = await session.execute(
        select(Customer).where(Customer.id == invoice.customer_id)
    )
    customer = customer_result.scalar_one()

    tmpl_result = await session.execute(
        select(InvoiceTemplate).where(InvoiceTemplate.mandant_id == mandant_id)
    )
    tmpl = tmpl_result.scalar_one_or_none() or InvoiceTemplate(mandant_id=mandant_id)

    li_dicts = [
        {
            "position": li.position,
            "description": li.description,
            "quantity": float(li.quantity),
            "unit": li.unit,
            "unit_price_cents": li.unit_price_cents,
            "vat_rate": float(li.vat_rate),
            "net_total_cents": li.net_total_cents,
            "vat_amount_cents": li.vat_amount_cents,
        }
        for li in line_items
    ]

    pdf_bytes = render_invoice_pdf(invoice, mandant, customer, li_dicts, tmpl)

    recipient = payload.override_email or (customer.email if customer.email else None)
    send_invoice_email(
        invoice, mandant, pdf_bytes, settings.secret_key, override_email=recipient
    )

    return {"sent": True, "recipient": recipient}
