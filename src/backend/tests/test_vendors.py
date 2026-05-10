"""Tests for vendor CRUD, vendor invoice lifecycle, and SEPA XML export."""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import ChartOfAccount
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password
from app.services.sepa_xml import (
    _validate_iban,
    generate_sepa_pain_001,
    SEPAPaymentInstruction,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


async def _add_ap_account(session: AsyncSession, mandant_id: uuid.UUID) -> None:
    """Add AP account 1600 (SKR03 Verbindlichkeiten) required for post_vendor_invoice.

    In production, migration 0009 backfills this. In tests we use create_all
    (no migrations), so we must insert it manually.
    """
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


async def _setup(session: AsyncSession) -> tuple[dict[str, str], User, Mandant]:
    """Create user + SKR03 mandant with AP account seeded."""
    user = User(
        email=f"vendor{uuid.uuid4()}@x.com",
        hashed_password=hash_password("pw"),
    )
    session.add(user)
    mandant = Mandant(
        name="Vendor Test GmbH",
        skr_variant="skr03",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
    )
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    # Add AP account that migration 0009 normally backfills
    await _add_ap_account(session, mandant.id)
    token = create_access_token(user.id, mandant.id)
    return {"Authorization": f"Bearer {token}"}, user, mandant


async def _get_expense_coa_id(session: AsyncSession, mandant_id: uuid.UUID) -> str:
    """Return account 4000 (SKR03 expense) for use as the SOLL account in postings."""
    result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.account_number == "4000",
        )
    )
    coa = result.scalar_one()
    return str(coa.id)


# ---------------------------------------------------------------------------
# Vendor CRUD
# ---------------------------------------------------------------------------


async def test_create_vendor(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _user, _mandant = await _setup(db_session)
    resp = await client.post(
        "/api/v1/vendors/",
        json={
            "name": "Muster Lieferant GmbH",
            "city": "Hamburg",
            "bank_iban": "DE89370400440532013000",
            "bank_bic": "COBADEFFXXX",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "Muster Lieferant GmbH"
    assert data["city"] == "Hamburg"
    assert data["bank_iban"] == "DE89370400440532013000"


async def test_list_vendors(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _user, _mandant = await _setup(db_session)
    await client.post(
        "/api/v1/vendors/",
        json={"name": "Vendor A"},
        headers=headers,
    )
    await client.post(
        "/api/v1/vendors/",
        json={"name": "Vendor B"},
        headers=headers,
    )
    resp = await client.get("/api/v1/vendors/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


async def test_get_vendor(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _user, _mandant = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/vendors/",
        json={"name": "Single Vendor"},
        headers=headers,
    )
    vendor_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/vendors/{vendor_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Single Vendor"


async def test_update_vendor(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, _user, _mandant = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/vendors/",
        json={"name": "Old Name"},
        headers=headers,
    )
    vendor_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/vendors/{vendor_id}",
        json={"name": "New Name", "city": "Berlin"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["city"] == "Berlin"


async def test_get_vendor_not_found(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _user, _mandant = await _setup(db_session)
    resp = await client.get(f"/api/v1/vendors/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Vendor Invoice lifecycle
# ---------------------------------------------------------------------------


async def _create_vendor_with_iban(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/vendors/",
        json={
            "name": "Test Lieferant AG",
            "bank_iban": "DE89370400440532013000",
            "bank_bic": "COBADEFFXXX",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_vendor_invoice(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _user, _mandant = await _setup(db_session)
    vendor_id = await _create_vendor_with_iban(client, headers)

    resp = await client.post(
        "/api/v1/vendor-invoices/",
        json={
            "vendor_id": vendor_id,
            "invoice_number": "LR-2024-001",
            "invoice_date": "2024-03-15",
            "due_date": "2024-04-15",
            "amount_cents": 11900,
            "vat_amount_cents": 1900,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "draft"
    assert data["amount_cents"] == 11900
    assert data["invoice_number"] == "LR-2024-001"


async def test_create_vendor_invoice_invalid_amount(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _user, _mandant = await _setup(db_session)
    vendor_id = await _create_vendor_with_iban(client, headers)
    resp = await client.post(
        "/api/v1/vendor-invoices/",
        json={
            "vendor_id": vendor_id,
            "invoice_number": "BAD-001",
            "invoice_date": "2024-03-15",
            "amount_cents": 0,
        },
        headers=headers,
    )
    assert resp.status_code == 422


async def test_post_vendor_invoice(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _user, mandant = await _setup(db_session)
    vendor_id = await _create_vendor_with_iban(client, headers)

    # Get an expense account id
    expense_coa_id = await _get_expense_coa_id(db_session, mandant.id)

    create_resp = await client.post(
        "/api/v1/vendor-invoices/",
        json={
            "vendor_id": vendor_id,
            "invoice_number": "LR-POST-001",
            "invoice_date": "2024-03-15",
            "amount_cents": 11900,
            "vat_amount_cents": 1900,
        },
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]

    post_resp = await client.post(
        f"/api/v1/vendor-invoices/{invoice_id}/post",
        json={"expense_coa_id": expense_coa_id},
        headers=headers,
    )
    assert post_resp.status_code == 200, post_resp.text
    data = post_resp.json()
    assert data["status"] == "posted"
    assert data["booking_id"] is not None


async def test_post_vendor_invoice_already_posted(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Posting a posted invoice returns 422 (GoBD immutability)."""
    headers, _user, mandant = await _setup(db_session)
    vendor_id = await _create_vendor_with_iban(client, headers)
    expense_coa_id = await _get_expense_coa_id(db_session, mandant.id)

    create_resp = await client.post(
        "/api/v1/vendor-invoices/",
        json={
            "vendor_id": vendor_id,
            "invoice_number": "LR-DUPE-001",
            "invoice_date": "2024-03-15",
            "amount_cents": 5000,
        },
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/vendor-invoices/{invoice_id}/post",
        json={"expense_coa_id": expense_coa_id},
        headers=headers,
    )
    # Try to post again
    second_post = await client.post(
        f"/api/v1/vendor-invoices/{invoice_id}/post",
        json={"expense_coa_id": expense_coa_id},
        headers=headers,
    )
    assert second_post.status_code == 422


async def test_mark_vendor_invoice_paid(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _user, mandant = await _setup(db_session)
    vendor_id = await _create_vendor_with_iban(client, headers)
    expense_coa_id = await _get_expense_coa_id(db_session, mandant.id)

    create_resp = await client.post(
        "/api/v1/vendor-invoices/",
        json={
            "vendor_id": vendor_id,
            "invoice_number": "LR-PAY-001",
            "invoice_date": "2024-03-15",
            "due_date": "2024-04-15",
            "amount_cents": 10000,
        },
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/vendor-invoices/{invoice_id}/post",
        json={"expense_coa_id": expense_coa_id},
        headers=headers,
    )
    pay_resp = await client.post(
        f"/api/v1/vendor-invoices/{invoice_id}/pay",
        headers=headers,
    )
    assert pay_resp.status_code == 200, pay_resp.text
    assert pay_resp.json()["status"] == "paid"


async def test_cancel_draft_vendor_invoice(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _user, _mandant = await _setup(db_session)
    vendor_id = await _create_vendor_with_iban(client, headers)

    create_resp = await client.post(
        "/api/v1/vendor-invoices/",
        json={
            "vendor_id": vendor_id,
            "invoice_number": "LR-CANCEL-001",
            "invoice_date": "2024-03-15",
            "amount_cents": 5000,
        },
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]

    cancel_resp = await client.post(
        f"/api/v1/vendor-invoices/{invoice_id}/cancel",
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


async def test_cancel_posted_invoice_fails(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """GoBD: posted invoices cannot be cancelled via this endpoint."""
    headers, _user, mandant = await _setup(db_session)
    vendor_id = await _create_vendor_with_iban(client, headers)
    expense_coa_id = await _get_expense_coa_id(db_session, mandant.id)

    create_resp = await client.post(
        "/api/v1/vendor-invoices/",
        json={
            "vendor_id": vendor_id,
            "invoice_number": "LR-GOBD-001",
            "invoice_date": "2024-03-15",
            "amount_cents": 5000,
        },
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/vendor-invoices/{invoice_id}/post",
        json={"expense_coa_id": expense_coa_id},
        headers=headers,
    )
    cancel_resp = await client.post(
        f"/api/v1/vendor-invoices/{invoice_id}/cancel",
        headers=headers,
    )
    assert cancel_resp.status_code == 422


async def test_list_vendor_invoices_filter_by_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _user, _mandant = await _setup(db_session)
    vendor_id = await _create_vendor_with_iban(client, headers)

    for i in range(2):
        await client.post(
            "/api/v1/vendor-invoices/",
            json={
                "vendor_id": vendor_id,
                "invoice_number": f"FILTER-{i:03d}",
                "invoice_date": "2024-03-15",
                "amount_cents": 1000,
            },
            headers=headers,
        )

    resp = await client.get("/api/v1/vendor-invoices/?status=draft", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert all(item["status"] == "draft" for item in data["items"])


# ---------------------------------------------------------------------------
# SEPA XML generation (unit-level)
# ---------------------------------------------------------------------------


def test_validate_iban_strips_spaces() -> None:
    iban = _validate_iban("DE89 3704 0044 0532 0130 00")
    assert iban == "DE89370400440532013000"


def test_validate_iban_too_short() -> None:
    with pytest.raises(ValueError, match="length"):
        _validate_iban("DE123")


def test_generate_sepa_pain_001_single_payment() -> None:
    payments = [
        SEPAPaymentInstruction(
            vendor_name="Muster GmbH",
            vendor_iban="DE89370400440532013000",
            vendor_bic="COBADEFFXXX",
            amount_cents=11900,
            currency="EUR",
            remittance_info="RE LR-2024-001",
            end_to_end_id="INV-abc123",
        )
    ]
    xml_bytes = generate_sepa_pain_001(
        mandant_name="Vendor Test GmbH",
        mandant_iban="DE89370400440532013000",
        mandant_bic="COBADEFFXXX",
        execution_date=date(2024, 4, 15),
        payments=payments,
    )
    assert isinstance(xml_bytes, bytes)
    xml_str = xml_bytes.decode("utf-8")
    assert "pain.001.003.03" in xml_str
    assert "Muster GmbH" in xml_str
    assert "DE89370400440532013000" in xml_str
    assert "119.00" in xml_str
    assert "RE LR-2024-001" in xml_str


def test_generate_sepa_pain_001_no_payments() -> None:
    with pytest.raises(ValueError, match="No payments"):
        generate_sepa_pain_001(
            mandant_name="Test",
            mandant_iban="DE89370400440532013000",
            mandant_bic="COBADEFFXXX",
            execution_date=date(2024, 4, 15),
            payments=[],
        )


def test_generate_sepa_pain_001_control_sum() -> None:
    """Verify CtrlSum equals sum of all payment amounts."""
    payments = [
        SEPAPaymentInstruction(
            vendor_name="A GmbH",
            vendor_iban="DE89370400440532013000",
            vendor_bic=None,
            amount_cents=10000,  # 100.00 EUR
            currency="EUR",
            remittance_info="RE-001",
            end_to_end_id="INV-001",
        ),
        SEPAPaymentInstruction(
            vendor_name="B AG",
            vendor_iban="DE89370400440532013000",
            vendor_bic="COBADEFFXXX",
            amount_cents=5050,  # 50.50 EUR
            currency="EUR",
            remittance_info="RE-002",
            end_to_end_id="INV-002",
        ),
    ]
    xml_str = generate_sepa_pain_001(
        mandant_name="Test",
        mandant_iban="DE89370400440532013000",
        mandant_bic="COBADEFFXXX",
        execution_date=date(2024, 4, 15),
        payments=payments,
    ).decode("utf-8")
    # Total = 150.50
    assert "150.50" in xml_str


# ---------------------------------------------------------------------------
# SEPA export endpoint
# ---------------------------------------------------------------------------


async def test_sepa_export_endpoint(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _user, mandant = await _setup(db_session)
    vendor_id = await _create_vendor_with_iban(client, headers)
    expense_coa_id = await _get_expense_coa_id(db_session, mandant.id)

    # Create and post a vendor invoice with a due date
    create_resp = await client.post(
        "/api/v1/vendor-invoices/",
        json={
            "vendor_id": vendor_id,
            "invoice_number": "SEPA-EXP-001",
            "invoice_date": "2024-03-01",
            "due_date": "2024-04-01",
            "amount_cents": 25000,
        },
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/vendor-invoices/{invoice_id}/post",
        json={"expense_coa_id": expense_coa_id},
        headers=headers,
    )

    export_resp = await client.post(
        "/api/v1/vendor-invoices/sepa-export",
        json={"due_on_or_before": "2024-04-30"},
        headers=headers,
    )
    assert export_resp.status_code == 200, export_resp.text
    assert export_resp.headers["content-type"] == "application/xml"
    assert "sepa-" in export_resp.headers["content-disposition"]
    xml_str = export_resp.content.decode("utf-8")
    assert "pain.001.003.03" in xml_str
    assert "250.00" in xml_str


async def test_sepa_export_no_due_invoices(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _user, _mandant = await _setup(db_session)
    resp = await client.post(
        "/api/v1/vendor-invoices/sepa-export",
        json={"due_on_or_before": "2020-01-01"},
        headers=headers,
    )
    # 409 because no invoices found for that date
    assert resp.status_code == 409


async def test_sepa_export_mandant_no_iban(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """If mandant has no IBAN, SEPA export must fail with 409."""
    user = User(
        email=f"noiban{uuid.uuid4()}@x.com",
        hashed_password=hash_password("pw"),
    )
    db_session.add(user)
    mandant = Mandant(name="No IBAN GmbH", skr_variant="skr03")  # no iban/bic
    db_session.add(mandant)
    await db_session.flush()
    db_session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await db_session.flush()
    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/vendor-invoices/sepa-export",
        json={"due_on_or_before": "2024-04-30"},
        headers=headers,
    )
    assert resp.status_code == 409
