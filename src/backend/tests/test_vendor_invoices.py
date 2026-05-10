"""Tests for vendor CRUD, vendor invoice lifecycle, GoBD compliance, and document integration.

This file focuses on coverage NOT present in test_vendors.py:
- Service-level lifecycle via direct service calls (GoBD assertions)
- Audit trail verification
- Document → VendorInvoice integration (T6)
- Entry number assignment (GoBD §11)
- Vorsteuer split (Sammelbuchung, UStG §15)
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import VendorInvoiceImmutableError
from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.models.mandant import Mandant
from app.models.period import AuditLog
from app.models.user import User, UserMandant
from app.models.vendor import Vendor, VendorInvoice
from app.schemas.document import ExtractionResult
from app.schemas.vendor import VendorCreate, VendorInvoiceCreate
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password
from app.services.vendor_invoice import (
    cancel_vendor_invoice,
    create_vendor,
    create_vendor_invoice,
    list_vendors,
    mark_vendor_invoice_paid,
    post_vendor_invoice,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _add_ap_account(session: AsyncSession, mandant_id: uuid.UUID) -> None:
    """Add SKR03 AP account 1600 (backfilled by migration 0009 in production)."""
    ap = ChartOfAccount(
        mandant_id=mandant_id,
        account_number="1600",
        name="Verbindlichkeiten aus Lieferungen und Leistungen",
        account_class="1xxx",
        skr_variant="skr03",
        is_custom=False,
        private_share_percent=0,
        is_active=True,
    )
    session.add(ap)
    await session.flush()


async def _add_vat_account(session: AsyncSession, mandant_id: uuid.UUID) -> uuid.UUID:
    """Add SKR03 Vorsteuer account 1576 (backfilled by migration 0009 in production)."""
    vat = ChartOfAccount(
        mandant_id=mandant_id,
        account_number="1576",
        name="Vorsteuer 19%",
        account_class="1xxx",
        skr_variant="skr03",
        is_custom=False,
        private_share_percent=0,
        is_active=True,
    )
    session.add(vat)
    await session.flush()
    return vat.id


async def _setup(
    session: AsyncSession,
) -> tuple[dict[str, str], User, Mandant, uuid.UUID]:
    """Create user + SKR03 mandant with full chart including AP and VAT accounts.

    Returns (auth_headers, user, mandant, vat_account_id).
    """
    user = User(
        email=f"vi{uuid.uuid4()}@x.com",
        hashed_password=hash_password("pw"),
    )
    session.add(user)
    mandant = Mandant(
        name="VendorInv Test GmbH",
        skr_variant="skr03",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
    )
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    await _add_ap_account(session, mandant.id)
    vat_account_id = await _add_vat_account(session, mandant.id)
    token = create_access_token(user.id, mandant.id)
    return {"Authorization": f"Bearer {token}"}, user, mandant, vat_account_id


async def _expense_coa_id(session: AsyncSession, mandant_id: uuid.UUID) -> uuid.UUID:
    """Return the ID for SKR03 account 4000 (expense)."""
    result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.account_number == "4000",
        )
    )
    return result.scalar_one().id


async def _make_vendor(session: AsyncSession, mandant: Mandant, user: User) -> Vendor:
    """Create and return a Vendor for the given mandant."""
    return await create_vendor(
        session,
        mandant.id,
        user.id,
        VendorCreate(
            name="Test Lieferant AG",
            bank_iban="DE89370400440532013000",
            bank_bic="COBADEFFXXX",
        ),
    )


async def _make_draft_invoice(
    session: AsyncSession, mandant: Mandant, user: User, vendor: Vendor
) -> VendorInvoice:
    """Create a draft VendorInvoice."""
    return await create_vendor_invoice(
        session,
        mandant.id,
        user.id,
        VendorInvoiceCreate(
            vendor_id=vendor.id,
            invoice_number=f"LR-{uuid.uuid4().hex[:8]}",
            invoice_date=date(2026, 3, 15),
            due_date=date(2026, 4, 15),
            amount_cents=11900,
            vat_amount_cents=1900,
        ),
    )


# ---------------------------------------------------------------------------
# Vendor CRUD (service-level)
# ---------------------------------------------------------------------------


async def test_create_vendor_service(db_session: AsyncSession) -> None:
    """create_vendor must persist and return a Vendor with correct fields."""
    _, user, mandant, _vat_id = await _setup(db_session)
    vendor = await create_vendor(
        db_session,
        mandant.id,
        user.id,
        VendorCreate(name="Muster Lieferant GmbH", city="Hamburg"),
    )
    assert vendor.id is not None
    assert vendor.name == "Muster Lieferant GmbH"
    assert vendor.city == "Hamburg"
    assert vendor.mandant_id == mandant.id


async def test_list_vendors_service(db_session: AsyncSession) -> None:
    """list_vendors must return all vendors for the mandant."""
    _, user, mandant, _vat_id = await _setup(db_session)
    for name in ("Alpha GmbH", "Beta AG"):
        await create_vendor(
            db_session,
            mandant.id,
            user.id,
            VendorCreate(name=name),
        )
    response = await list_vendors(db_session, mandant.id)
    assert response.total >= 2
    names = {v.name for v in response.items}
    assert "Alpha GmbH" in names
    assert "Beta AG" in names


# ---------------------------------------------------------------------------
# Vendor invoice lifecycle (service-level)
# ---------------------------------------------------------------------------


async def test_create_vendor_invoice_returns_draft(db_session: AsyncSession) -> None:
    """create_vendor_invoice must return a VendorInvoice with status='draft' and no booking_id."""
    _, user, mandant, _vat_id = await _setup(db_session)
    vendor = await _make_vendor(db_session, mandant, user)
    invoice = await _make_draft_invoice(db_session, mandant, user, vendor)

    assert invoice.status == "draft"
    assert invoice.booking_id is None
    assert invoice.amount_cents == 11900


async def test_post_vendor_invoice_creates_booking(db_session: AsyncSession) -> None:
    """post_vendor_invoice must create a posted Booking with correct accounts and entry_number.

    Without vat_coa_id, a single booking is created with the gross amount.
    """
    _, user, mandant, _vat_id = await _setup(db_session)
    vendor = await _make_vendor(db_session, mandant, user)
    invoice = await _make_draft_invoice(db_session, mandant, user, vendor)

    expense_id = await _expense_coa_id(db_session, mandant.id)

    posted = await post_vendor_invoice(
        db_session, invoice.id, mandant.id, user.id, expense_id, "skr03"
    )

    assert posted.status == "posted"
    assert posted.booking_id is not None

    # Verify the Booking was created correctly
    result = await db_session.execute(
        select(Booking).where(Booking.id == posted.booking_id)
    )
    booking = result.scalar_one()
    assert booking.status == "posted"
    assert booking.coa_id == expense_id

    # Counter account must be 1600 (AP for SKR03)
    ap_result = await db_session.execute(
        select(ChartOfAccount).where(ChartOfAccount.id == booking.counter_coa_id)
    )
    ap_acc = ap_result.scalar_one()
    assert ap_acc.account_number == "1600"

    # GoBD §11: entry_number must be assigned and positive
    assert booking.entry_number is not None
    assert booking.entry_number > 0


async def test_post_vendor_invoice_with_vat_split(db_session: AsyncSession) -> None:
    """With vat_coa_id, post_vendor_invoice creates a Sammelbuchung (UStG §15).

    Two Bookings must share the same entry_number and booking_group_id:
      - Primary: net amount (10000) to expense account
      - VAT:     VAT amount (1900)  to Vorsteuer account
    Both credit the AP account (1600).
    """
    _, user, mandant, vat_account_id = await _setup(db_session)
    vendor = await _make_vendor(db_session, mandant, user)
    invoice = await _make_draft_invoice(db_session, mandant, user, vendor)
    # invoice has amount_cents=11900, vat_amount_cents=1900

    expense_id = await _expense_coa_id(db_session, mandant.id)

    posted = await post_vendor_invoice(
        db_session,
        invoice.id,
        mandant.id,
        user.id,
        expense_id,
        "skr03",
        vat_coa_id=vat_account_id,
    )

    assert posted.status == "posted"
    assert posted.booking_id is not None

    # Fetch the primary booking
    primary_result = await db_session.execute(
        select(Booking).where(Booking.id == posted.booking_id)
    )
    primary = primary_result.scalar_one()
    assert primary.status == "posted"
    assert primary.amount_cents == 10000  # net = 11900 - 1900
    assert primary.coa_id == expense_id
    assert primary.entry_number is not None
    assert primary.entry_number > 0
    assert primary.booking_group_id is not None

    # Fetch the VAT booking — same entry_number and group
    vat_result = await db_session.execute(
        select(Booking).where(
            Booking.mandant_id == mandant.id,
            Booking.booking_group_id == primary.booking_group_id,
            Booking.id != primary.id,
        )
    )
    vat_booking = vat_result.scalar_one()
    assert vat_booking.status == "posted"
    assert vat_booking.amount_cents == 1900
    assert vat_booking.coa_id == vat_account_id
    assert vat_booking.entry_number == primary.entry_number  # Sammelbuchung
    assert vat_booking.booking_group_id == primary.booking_group_id

    # Both bookings must credit the AP account (1600)
    for bk in (primary, vat_booking):
        ap_result = await db_session.execute(
            select(ChartOfAccount).where(ChartOfAccount.id == bk.counter_coa_id)
        )
        ap_acc = ap_result.scalar_one()
        assert ap_acc.account_number == "1600"


async def test_posted_invoice_has_entry_number(db_session: AsyncSession) -> None:
    """After posting, the linked booking must have entry_number > 0 (GoBD §11)."""
    _, user, mandant, _vat_id = await _setup(db_session)
    vendor = await _make_vendor(db_session, mandant, user)
    invoice = await _make_draft_invoice(db_session, mandant, user, vendor)
    expense_id = await _expense_coa_id(db_session, mandant.id)

    posted = await post_vendor_invoice(
        db_session, invoice.id, mandant.id, user.id, expense_id, "skr03"
    )

    booking_result = await db_session.execute(
        select(Booking).where(Booking.id == posted.booking_id)
    )
    booking = booking_result.scalar_one()
    assert isinstance(booking.entry_number, int)
    assert booking.entry_number > 0


async def test_post_creates_audit_trail(db_session: AsyncSession) -> None:
    """post_vendor_invoice must write audit log entries for both booking and invoice."""
    _, user, mandant, _vat_id = await _setup(db_session)
    vendor = await _make_vendor(db_session, mandant, user)
    invoice = await _make_draft_invoice(db_session, mandant, user, vendor)
    expense_id = await _expense_coa_id(db_session, mandant.id)

    posted = await post_vendor_invoice(
        db_session, invoice.id, mandant.id, user.id, expense_id, "skr03"
    )

    # Audit entry for the invoice
    inv_audit = await db_session.execute(
        select(AuditLog).where(
            AuditLog.record_id == invoice.id,
            AuditLog.table_name == "vendor_invoices",
        )
    )
    assert len(inv_audit.scalars().all()) >= 1

    # Audit entry for the booking
    booking_audit = await db_session.execute(
        select(AuditLog).where(
            AuditLog.record_id == posted.booking_id,
            AuditLog.table_name == "bookings",
        )
    )
    assert len(booking_audit.scalars().all()) >= 1


async def test_post_vendor_invoice_rejects_non_draft(db_session: AsyncSession) -> None:
    """Posting an already-posted invoice must raise VendorInvoiceImmutableError (GoBD)."""
    _, user, mandant, _vat_id = await _setup(db_session)
    vendor = await _make_vendor(db_session, mandant, user)
    invoice = await _make_draft_invoice(db_session, mandant, user, vendor)
    expense_id = await _expense_coa_id(db_session, mandant.id)

    await post_vendor_invoice(
        db_session, invoice.id, mandant.id, user.id, expense_id, "skr03"
    )

    with pytest.raises(VendorInvoiceImmutableError):
        await post_vendor_invoice(
            db_session, invoice.id, mandant.id, user.id, expense_id, "skr03"
        )


async def test_mark_vendor_invoice_paid(db_session: AsyncSession) -> None:
    """Marking a posted invoice as paid must set status='paid'."""
    _, user, mandant, _vat_id = await _setup(db_session)
    vendor = await _make_vendor(db_session, mandant, user)
    invoice = await _make_draft_invoice(db_session, mandant, user, vendor)
    expense_id = await _expense_coa_id(db_session, mandant.id)

    await post_vendor_invoice(
        db_session, invoice.id, mandant.id, user.id, expense_id, "skr03"
    )
    paid = await mark_vendor_invoice_paid(db_session, invoice.id, mandant.id, user.id)

    assert paid.status == "paid"


async def test_cancel_vendor_invoice_draft(db_session: AsyncSession) -> None:
    """Cancelling a draft invoice must set status='cancelled'."""
    _, user, mandant, _vat_id = await _setup(db_session)
    vendor = await _make_vendor(db_session, mandant, user)
    invoice = await _make_draft_invoice(db_session, mandant, user, vendor)

    cancelled = await cancel_vendor_invoice(db_session, invoice.id, mandant.id, user.id)
    assert cancelled.status == "cancelled"


async def test_cancel_vendor_invoice_posted_raises(db_session: AsyncSession) -> None:
    """Cancelling a posted invoice must raise VendorInvoiceImmutableError (GoBD §14)."""
    _, user, mandant, _vat_id = await _setup(db_session)
    vendor = await _make_vendor(db_session, mandant, user)
    invoice = await _make_draft_invoice(db_session, mandant, user, vendor)
    expense_id = await _expense_coa_id(db_session, mandant.id)

    await post_vendor_invoice(
        db_session, invoice.id, mandant.id, user.id, expense_id, "skr03"
    )

    with pytest.raises(VendorInvoiceImmutableError):
        await cancel_vendor_invoice(db_session, invoice.id, mandant.id, user.id)


# ---------------------------------------------------------------------------
# Document integration (T6) — confirm with create_vendor_invoice flag
# ---------------------------------------------------------------------------


async def _upload_and_process(client, headers: dict) -> str:
    """Upload and process a document. Returns doc_id."""
    fake_pdf = b"%PDF-1.4 fake content for testing"
    upload_resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("rechnung.pdf", fake_pdf, "application/pdf")},
        headers=headers,
    )
    assert upload_resp.status_code == 201, upload_resp.text
    doc_id = upload_resp.json()["id"]

    mock_result = ExtractionResult(
        vendor_name="Muster Lieferant AG",
        total_amount_cents=11900,
        vat_amount_cents=1900,
        confidence_score=0.9,
    )
    with patch(
        "app.services.document.extract_document",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        process_resp = await client.post(
            f"/api/v1/documents/{doc_id}/process", headers=headers
        )
    assert process_resp.status_code == 200
    return doc_id


async def test_confirm_document_with_vendor_invoice_flag(
    client, db_session: AsyncSession
) -> None:
    """Confirming with create_vendor_invoice=True must create a draft VendorInvoice linked to the doc."""
    headers, user, mandant, _vat_id = await _setup(db_session)

    # Create a vendor via API so we have a vendor_id
    vendor_resp = await client.post(
        "/api/v1/vendors/",
        json={"name": "Doc Lieferant GmbH"},
        headers=headers,
    )
    assert vendor_resp.status_code == 201
    vendor_id = vendor_resp.json()["id"]

    # Use dummy coa_ids (confirm with vendor_invoice skips booking creation)
    accs = (
        (
            await db_session.execute(
                select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant.id)
            )
        )
        .scalars()
        .all()
    )
    debit_id = str(next(a for a in accs if a.account_class.startswith("4")).id)
    credit_id = str(next(a for a in accs if a.account_number == "1200").id)

    doc_id = await _upload_and_process(client, headers)

    confirm_resp = await client.post(
        f"/api/v1/documents/{doc_id}/confirm",
        json={
            "debit_coa_id": debit_id,
            "credit_coa_id": credit_id,
            "amount_cents": 11900,
            "booking_text": "Eingangsrechnung",
            "booking_date": "2026-03-15",
            "create_vendor_invoice": True,
            "vendor_id": vendor_id,
        },
        headers=headers,
    )
    assert confirm_resp.status_code == 200, confirm_resp.text
    doc_data = confirm_resp.json()
    assert doc_data["status"] == "booked"
    # When create_vendor_invoice=True, no raw booking is created on the document
    assert doc_data["booking_id"] is None

    # A VendorInvoice must exist linked to this document
    vi_result = await db_session.execute(
        select(VendorInvoice).where(
            VendorInvoice.mandant_id == mandant.id,
        )
    )
    vendor_invoices = vi_result.scalars().all()
    matching = [vi for vi in vendor_invoices if str(vi.document_id) == doc_id]
    assert len(matching) == 1
    assert matching[0].status == "draft"


async def test_confirm_document_without_vendor_invoice_flag(
    client, db_session: AsyncSession
) -> None:
    """Standard confirm (create_vendor_invoice=False) must create a posted Booking."""
    headers, _, mandant, _vat_id = await _setup(db_session)

    accs = (
        (
            await db_session.execute(
                select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant.id)
            )
        )
        .scalars()
        .all()
    )
    debit_id = str(next(a for a in accs if a.account_class.startswith("4")).id)
    credit_id = str(next(a for a in accs if a.account_number == "1200").id)

    doc_id = await _upload_and_process(client, headers)

    confirm_resp = await client.post(
        f"/api/v1/documents/{doc_id}/confirm",
        json={
            "debit_coa_id": debit_id,
            "credit_coa_id": credit_id,
            "amount_cents": 11900,
            "booking_text": "Standard Buchung",
            "booking_date": "2026-03-15",
            "create_vendor_invoice": False,
        },
        headers=headers,
    )
    assert confirm_resp.status_code == 200, confirm_resp.text
    data = confirm_resp.json()
    assert data["status"] == "booked"
    assert data["booking_id"] is not None

    # Verify the booking is posted
    booking_result = await db_session.execute(
        select(Booking).where(Booking.id == uuid.UUID(data["booking_id"]))
    )
    booking = booking_result.scalar_one()
    assert booking.status == "posted"
