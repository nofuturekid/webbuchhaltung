import uuid

from sqlalchemy import select

from app.models.account import ChartOfAccount
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password
from app.services.period import get_or_create_period


async def _setup(
    session,
) -> tuple[dict[str, str], User, Mandant]:
    user = User(email=f"p{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="Period GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    token = create_access_token(user.id, mandant.id)
    return {"Authorization": f"Bearer {token}"}, user, mandant


async def test_period_auto_created_on_first_booking(client, db_session):
    headers, user, mandant = await _setup(db_session)
    accs = (
        (
            await db_session.execute(
                select(ChartOfAccount)
                .where(ChartOfAccount.mandant_id == mandant.id)
                .limit(2)
            )
        )
        .scalars()
        .all()
    )
    await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-03-01",
            "amount_cents": 10000,
            "coa_id": str(accs[0].id),
            "counter_coa_id": str(accs[1].id),
        },
        headers=headers,
    )
    period = await get_or_create_period(db_session, mandant.id, 2026, 3)
    assert period.year == 2026
    assert period.month == 3


async def test_lock_then_archive_period(client, db_session):
    headers, user, mandant = await _setup(db_session)
    period = await get_or_create_period(db_session, mandant.id, 2025, 12)
    await db_session.flush()
    lock_resp = await client.post(f"/api/v1/periods/{period.id}/lock", headers=headers)
    assert lock_resp.status_code == 200
    assert lock_resp.json()["status"] == "locked"
    archive_resp = await client.post(
        f"/api/v1/periods/{period.id}/archive", headers=headers
    )
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "archived"


async def test_cannot_post_booking_into_locked_period(client, db_session):
    headers, user, mandant = await _setup(db_session)
    accs = (
        (
            await db_session.execute(
                select(ChartOfAccount)
                .where(ChartOfAccount.mandant_id == mandant.id)
                .limit(2)
            )
        )
        .scalars()
        .all()
    )
    period = await get_or_create_period(db_session, mandant.id, 2025, 6)
    await db_session.flush()
    lock_resp = await client.post(f"/api/v1/periods/{period.id}/lock", headers=headers)
    assert lock_resp.json()["status"] == "locked"
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2025-06-15",
            "amount_cents": 10000,
            "coa_id": str(accs[0].id),
            "counter_coa_id": str(accs[1].id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    post_resp = await client.post(
        f"/api/v1/bookings/{booking_id}/post", headers=headers
    )
    assert post_resp.status_code == 422
    assert post_resp.json()["error"]["code"] == "PERIOD_LOCKED"
