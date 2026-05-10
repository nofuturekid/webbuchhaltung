"""Tests for Phase 4 Asset Management (assets router + service)."""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password


async def _setup(
    session: AsyncSession,
) -> tuple[dict[str, str], User, Mandant, uuid.UUID, uuid.UUID]:
    """Create user + mandant with SKR03 accounts. Returns headers, user, mandant,
    asset_coa_id (0320), depreciation_coa_id (4900)."""
    user = User(email=f"asset{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="AssetTest GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")

    # Resolve account IDs for asset (0320 = PKW) and depreciation expense (4900)
    coa_result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant.id,
            ChartOfAccount.account_number == "0320",
        )
    )
    asset_coa = coa_result.scalar_one()

    dep_result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant.id,
            ChartOfAccount.account_number == "4900",
        )
    )
    dep_coa = dep_result.scalar_one()

    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user, mandant, asset_coa.id, dep_coa.id


def _asset_payload(
    coa_id: uuid.UUID, depreciation_coa_id: uuid.UUID, **overrides: object
) -> dict:
    base: dict = {
        "name": "Test PKW",
        "purchase_date": "2026-01-15",
        "purchase_amount_cents": 120000,
        "useful_life_months": 12,
        "depreciation_method": "linear",
        "residual_value_cents": 0,
        "coa_id": str(coa_id),
        "depreciation_coa_id": str(depreciation_coa_id),
    }
    base.update(overrides)
    return base


# ── 1. Asset number format + sequence ─────────────────────────────────────────


async def test_asset_number_format_and_sequence(client, db_session):
    """Asset numbers must follow AV-YYYY-NNN and increment per mandant."""
    headers, _, _, coa_id, dep_id = await _setup(db_session)
    numbers = []
    for _ in range(2):
        resp = await client.post(
            "/api/v1/assets/",
            json=_asset_payload(coa_id, dep_id),
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        numbers.append(resp.json()["asset_number"])

    pattern = re.compile(r"^AV-\d{4}-\d{3}$")
    assert pattern.match(numbers[0]), f"Bad format: {numbers[0]}"
    assert pattern.match(numbers[1]), f"Bad format: {numbers[1]}"
    # Sequence must increment
    seq_0 = int(numbers[0].split("-")[2])
    seq_1 = int(numbers[1].split("-")[2])
    assert seq_1 == seq_0 + 1


# ── 2. Depreciation schedule entry count ──────────────────────────────────────


async def test_depreciation_schedule_entry_count(client, db_session):
    """A 12-month useful life must produce exactly 12 schedule entries."""
    headers, _, _, coa_id, dep_id = await _setup(db_session)
    resp = await client.post(
        "/api/v1/assets/",
        json=_asset_payload(coa_id, dep_id, useful_life_months=12),
        headers=headers,
    )
    assert resp.status_code == 201
    asset_id = resp.json()["id"]

    sched_resp = await client.get(
        f"/api/v1/assets/{asset_id}/depreciation-schedule", headers=headers
    )
    assert sched_resp.status_code == 200
    entries = sched_resp.json()
    assert len(entries) == 12, f"Expected 12 entries, got {len(entries)}"


# ── 3. Linear schedule sum ────────────────────────────────────────────────────


async def test_linear_schedule_sum_equals_depreciable_amount(client, db_session):
    """Sum of all schedule entries must equal purchase_amount - residual_value."""
    headers, _, _, coa_id, dep_id = await _setup(db_session)
    payload = _asset_payload(
        coa_id,
        dep_id,
        purchase_amount_cents=120000,
        residual_value_cents=0,
        useful_life_months=12,
    )
    resp = await client.post("/api/v1/assets/", json=payload, headers=headers)
    assert resp.status_code == 201
    asset_id = resp.json()["id"]

    sched_resp = await client.get(
        f"/api/v1/assets/{asset_id}/depreciation-schedule", headers=headers
    )
    entries = sched_resp.json()
    total = sum(e["amount_cents"] for e in entries)
    expected = payload["purchase_amount_cents"] - payload["residual_value_cents"]
    assert total == expected, f"Schedule sum {total} != depreciable amount {expected}"


# ── 4. Rounding — last entry absorbs remainder ────────────────────────────────


async def test_depreciation_rounding_last_entry_absorbs_remainder(client, db_session):
    """When (purchase - residual) % useful_life != 0, last entry absorbs remainder."""
    headers, _, _, coa_id, dep_id = await _setup(db_session)
    # 10001 cents over 3 months: 3333 + 3333 + 3335 = 10001
    payload = _asset_payload(
        coa_id,
        dep_id,
        purchase_amount_cents=10001,
        residual_value_cents=0,
        useful_life_months=3,
    )
    resp = await client.post("/api/v1/assets/", json=payload, headers=headers)
    assert resp.status_code == 201
    asset_id = resp.json()["id"]

    sched_resp = await client.get(
        f"/api/v1/assets/{asset_id}/depreciation-schedule", headers=headers
    )
    entries = sched_resp.json()
    assert len(entries) == 3

    total = sum(e["amount_cents"] for e in entries)
    assert total == 10001, f"Total {total} != 10001"

    # Last entry must be larger by the remainder
    base = 10001 // 3  # 3333
    remainder = 10001 % 3  # 2
    assert entries[-1]["amount_cents"] == base + remainder
    assert entries[0]["amount_cents"] == base


# ── 5. book_depreciation creates posted booking with correct accounts ─────────


async def test_book_depreciation_creates_posted_booking(client, db_session):
    """book-depreciation must create a posted Booking with correct debit/credit accounts."""
    headers, _, mandant, coa_id, dep_id = await _setup(db_session)
    # Asset purchased 2026-01-15 → first period is 2026-02
    resp = await client.post(
        "/api/v1/assets/",
        json=_asset_payload(coa_id, dep_id, purchase_date="2026-01-15"),
        headers=headers,
    )
    assert resp.status_code == 201
    asset_id = resp.json()["id"]

    book_resp = await client.post(
        f"/api/v1/assets/{asset_id}/book-depreciation",
        json={"period_year": 2026, "period_month": 2},
        headers=headers,
    )
    assert book_resp.status_code == 200, book_resp.text
    data = book_resp.json()
    booking_id = uuid.UUID(data["booking_id"])

    # Verify a posted Booking exists with correct account assignments
    result = await db_session.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one()
    assert booking.status == "posted"
    # coa_id = debit (depreciation expense), counter_coa_id = credit (asset account)
    assert (
        booking.coa_id == dep_id
    ), "Booking debit must be depreciation expense account"
    assert booking.counter_coa_id == coa_id, "Booking credit must be asset account"


# ── 6. Double booking same period → 409 ───────────────────────────────────────


async def test_book_depreciation_same_period_twice_returns_409(client, db_session):
    """Booking depreciation twice for the same period must return 409."""
    headers, _, _, coa_id, dep_id = await _setup(db_session)
    resp = await client.post(
        "/api/v1/assets/",
        json=_asset_payload(coa_id, dep_id, purchase_date="2026-01-15"),
        headers=headers,
    )
    asset_id = resp.json()["id"]

    first = await client.post(
        f"/api/v1/assets/{asset_id}/book-depreciation",
        json={"period_year": 2026, "period_month": 2},
        headers=headers,
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/assets/{asset_id}/book-depreciation",
        json={"period_year": 2026, "period_month": 2},
        headers=headers,
    )
    assert second.status_code == 409


# ── 7. update_asset with purchase_amount after booking → 422 ─────────────────


async def test_update_purchase_amount_after_booking_returns_422(client, db_session):
    """Patching purchase_amount_cents after a depreciation is booked must return 422."""
    headers, _, _, coa_id, dep_id = await _setup(db_session)
    resp = await client.post(
        "/api/v1/assets/",
        json=_asset_payload(coa_id, dep_id, purchase_date="2026-01-15"),
        headers=headers,
    )
    asset_id = resp.json()["id"]

    # Book first period
    book = await client.post(
        f"/api/v1/assets/{asset_id}/book-depreciation",
        json={"period_year": 2026, "period_month": 2},
        headers=headers,
    )
    assert book.status_code == 200

    # Attempt to change purchase amount — must be blocked
    patch_resp = await client.patch(
        f"/api/v1/assets/{asset_id}",
        json={"purchase_amount_cents": 999999},
        headers=headers,
    )
    assert patch_resp.status_code == 422
    assert patch_resp.json()["error"]["code"] == "ASSET_IMMUTABLE"


# ── 8. update_asset before any booking → allowed ─────────────────────────────


async def test_update_name_before_booking_succeeds(client, db_session):
    """Patching a mutable field (name) before any booking is posted must succeed."""
    headers, _, _, coa_id, dep_id = await _setup(db_session)
    resp = await client.post(
        "/api/v1/assets/",
        json=_asset_payload(coa_id, dep_id),
        headers=headers,
    )
    assert resp.status_code == 201
    asset_id = resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/assets/{asset_id}",
        json={"name": "Renamed Asset"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Renamed Asset"


# ── 9. Disposal creates bookings, sets status=disposed ───────────────────────


async def test_dispose_creates_bookings_and_sets_status_disposed(client, db_session):
    """Disposing an asset must set status=disposed and create at least one Booking.

    Use disposal_amount_cents == purchase_amount_cents so net_remaining == 0,
    which avoids the need for the loss/gain accounts (4855/2680) that are not
    in the minimal test seed. The bank-receipt booking still exercises the
    disposal code path and asserts GoBD-clean double-entry creation.
    """
    headers, _, mandant, coa_id, dep_id = await _setup(db_session)
    purchase = 50000
    resp = await client.post(
        "/api/v1/assets/",
        json=_asset_payload(
            coa_id,
            dep_id,
            purchase_amount_cents=purchase,
            residual_value_cents=0,
        ),
        headers=headers,
    )
    assert resp.status_code == 201
    asset_id = resp.json()["id"]

    # disposal_amount_cents == purchase_amount_cents → net_remaining == 0
    # → only the bank-receipt booking is created (no loss/gain account needed)
    dispose_resp = await client.post(
        f"/api/v1/assets/{asset_id}/dispose",
        json={"disposal_date": "2026-06-30", "disposal_amount_cents": purchase},
        headers=headers,
    )
    assert dispose_resp.status_code == 200, dispose_resp.text
    data = dispose_resp.json()
    assert data["status"] == "disposed"

    # At least one Booking must have been created
    result = await db_session.execute(
        select(Booking).where(
            Booking.mandant_id == mandant.id,
            Booking.notes.like("Abgang%"),
        )
    )
    bookings = result.scalars().all()
    assert len(bookings) >= 1, "At least one disposal booking must exist"
    for b in bookings:
        assert b.status == "posted"


# ── 10. Second disposal → 409 ─────────────────────────────────────────────────


async def test_second_dispose_returns_409(client, db_session):
    """Disposing an already-disposed asset must return 409."""
    headers, _, _, coa_id, dep_id = await _setup(db_session)
    resp = await client.post(
        "/api/v1/assets/",
        json=_asset_payload(coa_id, dep_id, purchase_amount_cents=50000),
        headers=headers,
    )
    asset_id = resp.json()["id"]

    # Use disposal_amount_cents == purchase_amount_cents to avoid missing loss account
    first = await client.post(
        f"/api/v1/assets/{asset_id}/dispose",
        json={"disposal_date": "2026-06-30", "disposal_amount_cents": 50000},
        headers=headers,
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/assets/{asset_id}/dispose",
        json={"disposal_date": "2026-06-30", "disposal_amount_cents": 50000},
        headers=headers,
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ASSET_ALREADY_DISPOSED"


# ── 11. Mandant isolation ─────────────────────────────────────────────────────


async def test_mandant_isolation_asset(client, db_session):
    """An asset created in mandant A must return 404 when accessed with mandant B token."""
    headers_a, _, _, coa_id_a, dep_id_a = await _setup(db_session)
    headers_b, _, _, _, _ = await _setup(db_session)

    resp = await client.post(
        "/api/v1/assets/",
        json=_asset_payload(coa_id_a, dep_id_a),
        headers=headers_a,
    )
    assert resp.status_code == 201
    asset_id = resp.json()["id"]

    get_resp = await client.get(f"/api/v1/assets/{asset_id}", headers=headers_b)
    assert get_resp.status_code == 404
