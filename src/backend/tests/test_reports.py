import uuid

from sqlalchemy import select

from app.models.account import ChartOfAccount
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password


async def _setup_with_bookings(
    session, client
) -> tuple[dict[str, str], Mandant, ChartOfAccount, ChartOfAccount, ChartOfAccount]:
    user = User(email=f"r{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="Report GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}

    accs = (
        (
            await session.execute(
                select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant.id)
            )
        )
        .scalars()
        .all()
    )
    revenue = next(a for a in accs if a.account_class.startswith("8"))
    expense = next(a for a in accs if a.account_class.startswith("4"))
    bank = next(a for a in accs if a.account_number == "1200")

    # Revenue: revenue(coa_id=debit) / bank(counter=credit), 1190 EUR incl. 19% USt
    r1 = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 119000,
            "coa_id": str(revenue.id),
            "counter_coa_id": str(bank.id),
            "tax_rate": "0.19",
            "tax_amount_cents": 19000,
        },
        headers=headers,
    )
    await client.post(f"/api/v1/bookings/{r1.json()['id']}/post", headers=headers)

    # Expense: expense(coa_id=debit) / bank(counter=credit), 595 EUR incl. 19% VSt
    r2 = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-20",
            "amount_cents": 59500,
            "coa_id": str(expense.id),
            "counter_coa_id": str(bank.id),
            "tax_rate": "0.19",
            "tax_amount_cents": 9500,
        },
        headers=headers,
    )
    await client.post(f"/api/v1/bookings/{r2.json()['id']}/post", headers=headers)

    return headers, mandant, revenue, expense, bank


async def test_eur_betriebseinnahmen(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/eur?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["betriebseinnahmen_cents"] == 100000  # 119000 - 19000


async def test_eur_betriebsausgaben(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/eur?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    data = resp.json()
    assert data["betriebsausgaben_cents"] == 50000  # 59500 - 9500


async def test_eur_ust_virtual_account(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/eur?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    data = resp.json()
    assert data["ust_cents"] == 19000


async def test_eur_private_share_deduction(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    await client.patch(
        f"/api/v1/accounts/{expense.id}",
        json={"private_share_percent": 50},
        headers=headers,
    )
    resp = await client.get(
        "/api/v1/reports/eur?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    data = resp.json()
    item = next(
        i for i in data["items"] if i["account_number"] == expense.account_number
    )
    assert item["reportable_cents"] == 25000  # net 50000 * 50% = 25000


async def test_kontoauszug_running_balance(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        f"/api/v1/reports/account-statement"
        f"?account_id={bank.id}&date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["lines"]) == 2
    # Bank is counter_coa_id for both bookings (credited both times)
    assert data["lines"][0]["credit_cents"] == 119000
    assert data["lines"][1]["credit_cents"] == 59500
    # opening_balance = 0 (no prior bookings); bank credited both times
    assert data["opening_balance_cents"] == 0
    assert data["closing_balance_cents"] == -178500


async def test_eur_excludes_out_of_range_bookings(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    # Query a range that excludes both bookings (Jan 15 and Jan 20 are outside Feb)
    resp = await client.get(
        "/api/v1/reports/eur?date_from=2026-02-01&date_to=2026-02-28",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["betriebseinnahmen_cents"] == 0
    assert data["betriebsausgaben_cents"] == 0
    assert data["items"] == []


async def test_reports_mandant_isolation(client, db_session):
    headers1, mandant1, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    # Create second mandant with no bookings
    user2 = User(email=f"iso{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    db_session.add(user2)
    mandant2 = Mandant(name="IsoReport GmbH", skr_variant="skr03")
    db_session.add(mandant2)
    await db_session.flush()
    db_session.add(UserMandant(user_id=user2.id, mandant_id=mandant2.id, role="admin"))
    await db_session.flush()
    headers2 = {"Authorization": f"Bearer {create_access_token(user2.id, mandant2.id)}"}
    eur_resp = await client.get(
        "/api/v1/reports/eur?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers2,
    )
    assert eur_resp.status_code == 200
    assert eur_resp.json()["betriebseinnahmen_cents"] == 0
    assert eur_resp.json()["items"] == []
