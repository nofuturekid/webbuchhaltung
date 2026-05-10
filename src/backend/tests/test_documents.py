"""Tests for Phase 4 Document Capture (documents router + service)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import LLMExtractionError
from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.schemas.document import ExtractionResult
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password


async def _setup(
    session: AsyncSession,
) -> tuple[dict[str, str], User, Mandant, uuid.UUID, uuid.UUID]:
    """Create user + mandant with SKR03 accounts.
    Returns headers, user, mandant, debit_coa_id (4900), credit_coa_id (1200).
    """
    user = User(email=f"doc{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="DocTest GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")

    # Resolve two real account IDs for booking confirm tests
    debit_result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant.id,
            ChartOfAccount.account_number == "4900",
        )
    )
    debit_coa = debit_result.scalar_one()

    credit_result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant.id,
            ChartOfAccount.account_number == "1200",
        )
    )
    credit_coa = credit_result.scalar_one()

    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user, mandant, debit_coa.id, credit_coa.id


async def _upload_pdf(client, headers: dict) -> str:
    """Upload a minimal fake PDF and return the document id."""
    fake_pdf = b"%PDF-1.4 fake content for testing"
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("invoice.pdf", fake_pdf, "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ── 1. Upload PDF → 201, status=uploaded ──────────────────────────────────────


async def test_upload_pdf_returns_201_status_uploaded(client, db_session):
    """Uploading a PDF file must return 201 and set status='uploaded'."""
    headers, _, _, _, _ = await _setup(db_session)
    fake_pdf = b"%PDF-1.4 fake content for testing"
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", fake_pdf, "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "uploaded"
    assert data["filename"] == "test.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["file_size_bytes"] == len(fake_pdf)


# ── 2. Upload unsupported type → 422 ──────────────────────────────────────────


async def test_upload_unsupported_mime_type_returns_422(client, db_session):
    """Uploading a text/plain file must be rejected with 422."""
    headers, _, _, _, _ = await _setup(db_session)
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.txt", b"some text content", "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


# ── 3. Process → LLM called, status=processed ────────────────────────────────


async def test_process_document_calls_llm_and_sets_status_processed(client, db_session):
    """After /process, document status must be 'processed' with extracted_json set."""
    headers, _, _, _, _ = await _setup(db_session)
    doc_id = await _upload_pdf(client, headers)

    # Avoid using document_date (date object) in ExtractionResult because
    # model_dump() emits a Python date which SQLAlchemy's JSON column cannot
    # serialize without a custom encoder. The service stores the raw model_dump()
    # dict, so keep all values JSON-native types.
    mock_result = ExtractionResult(
        vendor_name="Test Lieferant GmbH",
        total_amount_cents=11900,
        vat_amount_cents=1900,
        suggested_debit_account="4900",
        suggested_credit_account="1200",
        booking_text="Rechnung Test Lieferant",
        confidence_score=0.95,
    )

    with patch(
        "app.services.document.extract_document",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "processed"
    assert data["extracted_json"] is not None
    assert data["extracted_json"]["vendor_name"] == "Test Lieferant GmbH"
    assert data["extracted_json"]["total_amount_cents"] == 11900
    assert data["extracted_json"]["confidence_score"] == pytest.approx(0.95)


# ── 4. Process with LLM failure → 502 ────────────────────────────────────────


async def test_process_document_llm_failure_returns_502(client, db_session):
    """If the LLM extraction raises LLMExtractionError, /process must return 502."""
    headers, _, _, _, _ = await _setup(db_session)
    doc_id = await _upload_pdf(client, headers)

    with patch(
        "app.services.document.extract_document",
        new_callable=AsyncMock,
        side_effect=LLMExtractionError("API unavailable"),
    ):
        resp = await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "LLM_EXTRACTION_FAILED"


# ── 5. Booking suggestion resolves account UUIDs ──────────────────────────────


async def test_booking_suggestion_resolves_account_uuids(client, db_session):
    """GET /suggestion must return debit_coa_id and credit_coa_id as UUID or None."""
    headers, _, _, debit_id, credit_id = await _setup(db_session)
    doc_id = await _upload_pdf(client, headers)

    # Suggest accounts that exist in the seeded SKR03 chart
    mock_result = ExtractionResult(
        suggested_debit_account="4900",
        suggested_credit_account="1200",
        total_amount_cents=5000,
        confidence_score=0.8,
    )

    with patch(
        "app.services.document.extract_document",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)

    sug_resp = await client.get(
        f"/api/v1/documents/{doc_id}/suggestion", headers=headers
    )
    assert sug_resp.status_code == 200
    data = sug_resp.json()
    # Both accounts exist in SKR03 seed → UUIDs must be returned
    assert data["debit_coa_id"] is not None
    assert data["credit_coa_id"] is not None
    # Must be valid UUID strings
    uuid.UUID(data["debit_coa_id"])
    uuid.UUID(data["credit_coa_id"])


# ── 6. Confirm → Booking posted, status=booked ───────────────────────────────


async def test_confirm_document_creates_posted_booking(client, db_session):
    """Confirming a processed document must create a posted Booking and set status='booked'."""
    headers, _, mandant, debit_id, credit_id = await _setup(db_session)
    doc_id = await _upload_pdf(client, headers)

    mock_result = ExtractionResult(total_amount_cents=5000, confidence_score=0.9)
    with patch(
        "app.services.document.extract_document",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)

    confirm_resp = await client.post(
        f"/api/v1/documents/{doc_id}/confirm",
        json={
            "debit_coa_id": str(debit_id),
            "credit_coa_id": str(credit_id),
            "amount_cents": 5000,
            "booking_text": "Testbuchung Beleg",
            "booking_date": "2026-05-10",
        },
        headers=headers,
    )
    assert confirm_resp.status_code == 200, confirm_resp.text
    data = confirm_resp.json()
    assert data["status"] == "booked"
    assert data["booking_id"] is not None

    # Verify the Booking exists in the DB and is posted
    booking_id = uuid.UUID(data["booking_id"])
    result = await db_session.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one()
    assert booking.status == "posted"
    assert booking.coa_id == debit_id
    assert booking.counter_coa_id == credit_id
    assert booking.amount_cents == 5000


# ── 7. Confirm already-booked → 409 ──────────────────────────────────────────


async def test_confirm_already_booked_document_returns_409(client, db_session):
    """Confirming a document that is already 'booked' must return 409."""
    headers, _, _, debit_id, credit_id = await _setup(db_session)
    doc_id = await _upload_pdf(client, headers)

    mock_result = ExtractionResult(total_amount_cents=5000, confidence_score=0.9)
    with patch(
        "app.services.document.extract_document",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)

    confirm_payload = {
        "debit_coa_id": str(debit_id),
        "credit_coa_id": str(credit_id),
        "amount_cents": 5000,
        "booking_text": "Testbuchung Beleg",
        "booking_date": "2026-05-10",
    }
    first = await client.post(
        f"/api/v1/documents/{doc_id}/confirm", json=confirm_payload, headers=headers
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/documents/{doc_id}/confirm", json=confirm_payload, headers=headers
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DOCUMENT_ALREADY_BOOKED"


# ── 8. Reject → status=rejected ──────────────────────────────────────────────


async def test_reject_document_sets_status_rejected(client, db_session):
    """Calling /reject on an uploaded document must set status='rejected'."""
    headers, _, _, _, _ = await _setup(db_session)
    doc_id = await _upload_pdf(client, headers)

    reject_resp = await client.post(
        f"/api/v1/documents/{doc_id}/reject", headers=headers
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"


# ── 9. Mandant isolation ──────────────────────────────────────────────────────


async def test_mandant_isolation_document(client, db_session):
    """A document created in mandant A must return 404 when accessed with mandant B token."""
    headers_a, _, _, _, _ = await _setup(db_session)
    headers_b, _, _, _, _ = await _setup(db_session)

    doc_id = await _upload_pdf(client, headers_a)

    get_resp = await client.get(f"/api/v1/documents/{doc_id}", headers=headers_b)
    assert get_resp.status_code == 404
