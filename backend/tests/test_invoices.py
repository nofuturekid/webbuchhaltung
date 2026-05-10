import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Customer
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password


async def _setup(
    session: AsyncSession,
) -> tuple[dict[str, str], User, Mandant, Customer]:
    """Create a user, mandant with SKR03 accounts, and a test customer."""
    user = User(email=f"inv{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="InvTest GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")

    customer = Customer(
        mandant_id=mandant.id,
        name="Testkunde GmbH",
        email="kunde@example.com",
        street="Musterstraße 1",
        postal_code="12345",
        city="Berlin",
    )
    session.add(customer)
    await session.flush()

    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user, mandant, customer


def _invoice_payload(customer_id: uuid.UUID) -> dict:
    return {
        "customer_id": str(customer_id),
        "issue_date": "2026-05-01",
        "due_date": "2026-05-15",
        "notes": "Testnote",
        "line_items": [
            {
                "position": 1,
                "description": "Beratungsleistung",
                "quantity": "1.000",
                "unit": "Stunden",
                "unit_price_cents": 10000,
                "vat_rate": "0.19",
            }
        ],
    }


async def test_create_draft_invoice_returns_201(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    resp = await client.post(
        "/api/v1/invoices/",
        json=_invoice_payload(customer.id),
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "draft"
    assert data["invoice_number"].startswith("RE-")
    assert data["invoice_number"].endswith("-001")
    assert len(data["line_items"]) == 1


async def test_create_invoice_computes_totals(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    resp = await client.post(
        "/api/v1/invoices/",
        json=_invoice_payload(customer.id),
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    # 10000 * 1.0 = 10000 net, 10000 * 0.19 = 1900 vat, 11900 gross
    assert data["net_total_cents"] == 10000
    assert data["vat_total_cents"] == 1900
    assert data["gross_total_cents"] == 11900


async def test_get_invoice_returns_200(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/invoices/",
        json=_invoice_payload(customer.id),
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]
    get_resp = await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == invoice_id


async def test_issue_draft_invoice_returns_200_status_issued(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/invoices/",
        json=_invoice_payload(customer.id),
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]
    issue_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/issue", headers=headers
    )
    assert issue_resp.status_code == 200, issue_resp.text
    data = issue_resp.json()
    assert data["status"] == "issued"
    assert data["booking_id"] is not None


async def test_put_on_issued_invoice_returns_403(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/invoices/",
        json=_invoice_payload(customer.id),
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]
    await client.post(f"/api/v1/invoices/{invoice_id}/issue", headers=headers)
    put_resp = await client.put(
        f"/api/v1/invoices/{invoice_id}",
        json={"notes": "Versuch"},
        headers=headers,
    )
    assert put_resp.status_code == 403
    assert put_resp.json()["error"]["code"] == "INVOICE_IMMUTABLE"


async def test_issue_already_issued_invoice_returns_400(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/invoices/",
        json=_invoice_payload(customer.id),
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]
    await client.post(f"/api/v1/invoices/{invoice_id}/issue", headers=headers)
    second_issue = await client.post(
        f"/api/v1/invoices/{invoice_id}/issue", headers=headers
    )
    assert second_issue.status_code == 400
    assert second_issue.json()["error"]["code"] == "INVALID_INVOICE_STATE"


async def test_cancel_issued_invoice_returns_200_status_cancelled(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/invoices/",
        json=_invoice_payload(customer.id),
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]
    await client.post(f"/api/v1/invoices/{invoice_id}/issue", headers=headers)
    cancel_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/cancel", headers=headers
    )
    assert cancel_resp.status_code == 200, cancel_resp.text
    assert cancel_resp.json()["status"] == "cancelled"


async def test_delete_draft_invoice_returns_204(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/invoices/",
        json=_invoice_payload(customer.id),
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/api/v1/invoices/{invoice_id}", headers=headers)
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_delete_issued_invoice_returns_403(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/invoices/",
        json=_invoice_payload(customer.id),
        headers=headers,
    )
    invoice_id = create_resp.json()["id"]
    await client.post(f"/api/v1/invoices/{invoice_id}/issue", headers=headers)
    del_resp = await client.delete(f"/api/v1/invoices/{invoice_id}", headers=headers)
    assert del_resp.status_code == 403
    assert del_resp.json()["error"]["code"] == "INVOICE_IMMUTABLE"


async def test_list_invoices_returns_200(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    for _ in range(2):
        await client.post(
            "/api/v1/invoices/",
            json=_invoice_payload(customer.id),
            headers=headers,
        )
    resp = await client.get("/api/v1/invoices/", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_mandant_isolation_invoices(client, db_session):
    headers1, user1, mandant1, customer1 = await _setup(db_session)
    headers2, user2, mandant2, customer2 = await _setup(db_session)
    create_resp = await client.post(
        "/api/v1/invoices/",
        json=_invoice_payload(customer1.id),
        headers=headers1,
    )
    invoice_id = create_resp.json()["id"]
    get_resp = await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers2)
    assert get_resp.status_code == 404


async def test_invoice_number_increments_sequentially(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    nums = []
    for _ in range(3):
        r = await client.post(
            "/api/v1/invoices/",
            json=_invoice_payload(customer.id),
            headers=headers,
        )
        nums.append(r.json()["invoice_number"])
    assert nums[0].endswith("-001")
    assert nums[1].endswith("-002")
    assert nums[2].endswith("-003")


async def test_create_customer_and_list(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    resp = await client.post(
        "/api/v1/customers/",
        json={"name": "Neukunde AG", "country": "DE"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Neukunde AG"

    list_resp = await client.get("/api/v1/customers/", headers=headers)
    assert list_resp.status_code == 200
    names = [c["name"] for c in list_resp.json()]
    assert "Neukunde AG" in names


async def test_invalid_vat_rate_rejected(client, db_session):
    headers, user, mandant, customer = await _setup(db_session)
    payload = _invoice_payload(customer.id)
    payload["line_items"][0]["vat_rate"] = "0.10"  # invalid rate
    resp = await client.post("/api/v1/invoices/", json=payload, headers=headers)
    assert resp.status_code == 422
