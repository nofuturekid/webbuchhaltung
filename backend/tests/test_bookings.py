import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password


async def _setup(
    session: AsyncSession,
) -> tuple[dict[str, str], User, Mandant, ChartOfAccount, ChartOfAccount]:
    user = User(email=f"b{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="BookTest GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    from sqlalchemy import select

    result = await session.execute(
        select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant.id).limit(2)
    )
    accounts = result.scalars().all()
    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user, mandant, accounts[0], accounts[1]


async def test_create_booking_draft(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 119000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert data["entry_number"] is None
    assert data["created_by"] == str(user.id)


async def test_update_draft_booking(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 100000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    resp2 = await client.patch(
        f"/api/v1/bookings/{booking_id}",
        json={"notes": "Updated"},
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["notes"] == "Updated"


async def test_delete_draft_booking(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 100000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    del_resp = await client.delete(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_mandant_isolation_bookings(client, db_session):
    headers1, _, mandant1, acc1, acc2 = await _setup(db_session)
    user2 = User(email=f"iso{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    db_session.add(user2)
    mandant2 = Mandant(name="Other GmbH", skr_variant="skr03")
    db_session.add(mandant2)
    await db_session.flush()
    db_session.add(UserMandant(user_id=user2.id, mandant_id=mandant2.id, role="admin"))
    await db_session.flush()
    headers2 = {"Authorization": f"Bearer {create_access_token(user2.id, mandant2.id)}"}
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 100000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers1,
    )
    booking_id = resp.json()["id"]
    get_resp = await client.get(f"/api/v1/bookings/{booking_id}", headers=headers2)
    assert get_resp.status_code == 404


async def test_amount_validation_rejects_zero(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 0,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    assert resp.status_code == 422


async def test_notes_validation_rejects_long_text(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 100,
            "notes": "x" * 61,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    assert resp.status_code == 422


async def test_list_bookings_returns_paginated(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    for _ in range(3):
        await client.post(
            "/api/v1/bookings",
            json={
                "date_booking": "2026-01-15",
                "amount_cents": 100,
                "coa_id": str(acc1.id),
                "counter_coa_id": str(acc2.id),
            },
            headers=headers,
        )
    resp = await client.get("/api/v1/bookings", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 50


async def test_cannot_update_or_delete_posted_booking(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 100000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    # Force-post the booking directly in DB (posting endpoint is Task 8)
    from sqlalchemy import update

    await db_session.execute(
        update(Booking)
        .where(Booking.id == uuid.UUID(booking_id))
        .values(status="posted", entry_number=1)
    )
    await db_session.flush()
    patch_resp = await client.patch(
        f"/api/v1/bookings/{booking_id}", json={"notes": "Attempt"}, headers=headers
    )
    assert patch_resp.status_code == 422
    assert patch_resp.json()["error"]["code"] == "BOOKING_ALREADY_POSTED"
    delete_resp = await client.delete(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert delete_resp.status_code == 422
    assert delete_resp.json()["error"]["code"] == "BOOKING_ALREADY_POSTED"
