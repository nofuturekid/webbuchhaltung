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


# ---------------------------------------------------------------------------
# Saldenliste tests
# ---------------------------------------------------------------------------


async def test_saldenliste_returns_rows(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/saldenliste?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "rows" in data
    assert "total_debit_cents" in data
    assert "total_credit_cents" in data
    # At least the revenue, expense, and bank accounts should appear
    assert len(data["rows"]) >= 3


async def test_saldenliste_totals(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/saldenliste?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    data = resp.json()
    # Total debit = sum of all period_debit_cents across rows
    assert data["total_debit_cents"] == sum(
        r["period_debit_cents"] for r in data["rows"]
    )
    assert data["total_credit_cents"] == sum(
        r["period_credit_cents"] for r in data["rows"]
    )


async def test_saldenliste_closing_balance(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/saldenliste?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    data = resp.json()
    for row in data["rows"]:
        expected_closing = (
            row["opening_balance_cents"]
            + row["period_debit_cents"]
            - row["period_credit_cents"]
        )
        assert (
            row["closing_balance_cents"] == expected_closing
        ), f"Account {row['account_number']} closing balance mismatch"


async def test_saldenliste_csv_format(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/saldenliste?date_from=2026-01-01&date_to=2026-01-31&format=csv",
        headers=headers,
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    # CSV must have header row + at least one data row
    lines = resp.text.strip().splitlines()
    assert len(lines) >= 2
    assert "Account Number" in lines[0]


async def test_saldenliste_excludes_zero_accounts(client, db_session):
    # A mandant with no bookings — saldenliste should return no rows
    user = User(email=f"sal{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    db_session.add(user)
    mandant = Mandant(name="Empty Sal GmbH", skr_variant="skr03")
    db_session.add(mandant)
    await db_session.flush()
    db_session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await db_session.flush()
    await seed_skr_for_mandant(db_session, mandant.id, "skr03")
    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(
        "/api/v1/reports/saldenliste?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["rows"] == []


# ---------------------------------------------------------------------------
# Bilanz tests
# ---------------------------------------------------------------------------


async def test_bilanz_returns_aktiva_passiva(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/bilanz?as_of_date=2026-01-31",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "aktiva" in data
    assert "passiva" in data
    assert "aktiva_total_cents" in data
    assert "passiva_total_cents" in data
    assert "balanced" in data
    assert "imbalance_cents" in data


async def test_bilanz_imbalance_non_negative(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/bilanz?as_of_date=2026-01-31",
        headers=headers,
    )
    data = resp.json()
    assert data["imbalance_cents"] >= 0
    if data["balanced"]:
        assert data["imbalance_cents"] == 0
    else:
        assert data["imbalance_cents"] > 0


async def test_bilanz_sections_labels(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/bilanz?as_of_date=2026-01-31",
        headers=headers,
    )
    data = resp.json()
    aktiva_labels = {s["label"] for s in data["aktiva"]}
    passiva_labels = {s["label"] for s in data["passiva"]}
    assert "A. Anlagevermögen" in aktiva_labels
    assert "B. Umlaufvermögen" in aktiva_labels
    assert "A. Eigenkapital" in passiva_labels
    assert "B. Verbindlichkeiten" in passiva_labels


# ---------------------------------------------------------------------------
# G+V tests
# ---------------------------------------------------------------------------


async def test_guv_returns_structure(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/guv?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "revenue_rows" in data
    assert "expense_rows" in data
    assert "revenue_total_cents" in data
    assert "expense_total_cents" in data
    assert "result_cents" in data


async def test_guv_result_is_revenue_minus_expenses(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/guv?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    data = resp.json()
    assert (
        data["result_cents"]
        == data["revenue_total_cents"] - data["expense_total_cents"]
    )


async def test_guv_skr03_revenue_in_8xxx(client, db_session):
    # Revenue booking goes to an 8xxx account → should appear in revenue_rows
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/guv?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    data = resp.json()
    # revenue.account_class starts with "8" for SKR03 — must be in revenue_rows
    assert data["revenue_total_cents"] > 0
    assert len(data["revenue_rows"]) > 0


async def test_guv_empty_period_returns_zeros(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/guv?date_from=2025-01-01&date_to=2025-12-31",
        headers=headers,
    )
    data = resp.json()
    assert data["revenue_total_cents"] == 0
    assert data["expense_total_cents"] == 0
    assert data["result_cents"] == 0


# ---------------------------------------------------------------------------
# BWA tests
# ---------------------------------------------------------------------------


async def test_bwa_returns_12_months(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/bwa?year=2026",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == 2026
    assert len(data["columns"]) == 12
    months = [col["month"] for col in data["columns"]]
    assert months == list(range(1, 13))


async def test_bwa_january_has_revenue(client, db_session):
    # The setup creates a revenue booking in Jan 2026 (119000 cents)
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/bwa?year=2026",
        headers=headers,
    )
    data = resp.json()
    jan = next(col for col in data["columns"] if col["month"] == 1)
    # Revenue account (8xxx SKR03) → revenue_cents should be positive
    assert jan["revenue_cents"] > 0


async def test_bwa_empty_months_are_zero(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/bwa?year=2026",
        headers=headers,
    )
    data = resp.json()
    # Months 2-12 should have zero revenue since bookings are only in January
    for col in data["columns"]:
        if col["month"] != 1:
            assert col["revenue_cents"] == 0, f"Month {col['month']} should be 0"


async def test_bwa_ytd_totals(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(
        db_session, client
    )
    resp = await client.get(
        "/api/v1/reports/bwa?year=2026",
        headers=headers,
    )
    data = resp.json()
    expected_ytd_revenue = sum(col["revenue_cents"] for col in data["columns"])
    expected_ytd_ebit = sum(col["ebit_cents"] for col in data["columns"])
    assert data["ytd_revenue_cents"] == expected_ytd_revenue
    assert data["ytd_ebit_cents"] == expected_ytd_ebit
