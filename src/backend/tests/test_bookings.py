import uuid

from sqlalchemy import select, update
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


async def test_cannot_update_or_delete_reversed_booking(client, db_session):
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
    await db_session.execute(
        update(Booking)
        .where(Booking.id == uuid.UUID(booking_id))
        .values(status="reversed", entry_number=1)
    )
    await db_session.flush()
    patch_resp = await client.patch(
        f"/api/v1/bookings/{booking_id}", json={"notes": "Attempt"}, headers=headers
    )
    assert patch_resp.status_code == 422
    delete_resp = await client.delete(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert delete_resp.status_code == 422


async def test_post_booking_assigns_entry_number(client, db_session):
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
    booking_id = resp.json()["id"]
    post_resp = await client.post(
        f"/api/v1/bookings/{booking_id}/post", headers=headers
    )
    assert post_resp.status_code == 200
    data = post_resp.json()
    assert data["status"] == "posted"
    assert data["entry_number"] is not None
    assert isinstance(data["entry_number"], int)


async def test_posted_booking_is_immutable(client, db_session):
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
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    patch_resp = await client.patch(
        f"/api/v1/bookings/{booking_id}", json={"notes": "x"}, headers=headers
    )
    assert patch_resp.status_code == 422
    assert patch_resp.json()["error"]["code"] == "BOOKING_ALREADY_POSTED"
    del_resp = await client.delete(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert del_resp.status_code == 422


async def test_entry_numbers_are_sequential_no_gaps(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    ids = []
    for _ in range(3):
        r = await client.post(
            "/api/v1/bookings",
            json={
                "date_booking": "2026-01-15",
                "amount_cents": 10000,
                "coa_id": str(acc1.id),
                "counter_coa_id": str(acc2.id),
            },
            headers=headers,
        )
        ids.append(r.json()["id"])
    numbers = []
    for bid in ids:
        r = await client.post(f"/api/v1/bookings/{bid}/post", headers=headers)
        numbers.append(r.json()["entry_number"])
    assert numbers == sorted(numbers)
    assert len(set(numbers)) == 3


async def test_audit_log_written_on_post(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 50000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    log_resp = await client.get(
        f"/api/v1/bookings/{booking_id}/audit-log", headers=headers
    )
    assert log_resp.status_code == 200
    entries = log_resp.json()
    assert len(entries) >= 1
    assert entries[-1]["action"] == "update"
    assert "status" in entries[-1]["change_summary"]


async def test_cannot_post_already_posted_booking(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 10000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    resp2 = await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    assert resp2.status_code == 422
    assert resp2.json()["error"]["code"] == "BOOKING_ALREADY_POSTED"


async def test_audit_log_mandant_isolation(client, db_session):
    headers1, user1, mandant1, acc1, acc2 = await _setup(db_session)
    user2 = User(email=f"aud{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    db_session.add(user2)
    mandant2 = Mandant(name="AuditIso GmbH", skr_variant="skr03")
    db_session.add(mandant2)
    await db_session.flush()
    db_session.add(UserMandant(user_id=user2.id, mandant_id=mandant2.id, role="admin"))
    await db_session.flush()
    headers2 = {"Authorization": f"Bearer {create_access_token(user2.id, mandant2.id)}"}
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 10000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers1,
    )
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers1)
    log_resp = await client.get(
        f"/api/v1/bookings/{booking_id}/audit-log", headers=headers2
    )
    assert log_resp.status_code == 404


async def test_reversal_swaps_accounts_and_posts(client, db_session):
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
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)

    rev_resp = await client.post(
        f"/api/v1/bookings/{booking_id}/reverse", headers=headers
    )
    assert rev_resp.status_code == 200
    rev = rev_resp.json()
    assert rev["status"] == "posted"
    assert rev["coa_id"] == str(acc2.id)
    assert rev["counter_coa_id"] == str(acc1.id)
    assert rev["reversal_of_id"] == booking_id
    assert rev["entry_number"] is not None
    assert isinstance(rev["entry_number"], int)


async def test_reversal_marks_original_as_reversed(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 50000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    await client.post(f"/api/v1/bookings/{booking_id}/reverse", headers=headers)

    orig_resp = await client.get(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert orig_resp.json()["status"] == "reversed"


async def test_cannot_reverse_draft_booking(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 50000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    rev_resp = await client.post(
        f"/api/v1/bookings/{booking_id}/reverse", headers=headers
    )
    assert rev_resp.status_code == 409


async def test_cannot_reverse_already_reversed_booking(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 50000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    await client.post(f"/api/v1/bookings/{booking_id}/reverse", headers=headers)
    rev_again = await client.post(
        f"/api/v1/bookings/{booking_id}/reverse", headers=headers
    )
    assert rev_again.status_code == 409


async def test_cannot_re_reverse_a_reversal_booking(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 50000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    rev_resp = await client.post(
        f"/api/v1/bookings/{booking_id}/reverse", headers=headers
    )
    reversal_id = rev_resp.json()["id"]
    re_rev = await client.post(
        f"/api/v1/bookings/{reversal_id}/reverse", headers=headers
    )
    assert re_rev.status_code == 409
