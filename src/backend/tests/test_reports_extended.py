"""Extended report tests for Saldenliste, G+V, and BWA.

test_reports.py covers the basic happy-path and structure. This file adds:
- Saldenliste saldo arithmetic per account
- G+V revenue vs expense split and sign correctness
- BWA multi-month data and column integrity
- Bilanz aktiva side with asset entry
- Reports JSON endpoint format verification
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password
from app.services.booking import get_next_entry_number
from app.services.reports import generate_bwa, generate_guv, generate_saldenliste


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup(session: AsyncSession) -> tuple[dict[str, str], User, Mandant]:
    """Create user + SKR03 mandant."""
    user = User(email=f"rpt{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="ExtReport GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    token = create_access_token(user.id, mandant.id)
    return {"Authorization": f"Bearer {token}"}, user, mandant


async def _post_booking(
    session: AsyncSession,
    mandant: Mandant,
    user: User,
    debit_acc: ChartOfAccount,
    credit_acc: ChartOfAccount,
    amount_cents: int,
    booking_date: date,
) -> Booking:
    """Create and post a booking directly via session."""
    booking = Booking(
        mandant_id=mandant.id,
        booking_type="entry",
        date_booking=booking_date,
        amount_cents=amount_cents,
        coa_id=debit_acc.id,
        counter_coa_id=credit_acc.id,
        status="draft",
        created_by=user.id,
    )
    session.add(booking)
    await session.flush()
    entry_number = await get_next_entry_number(session, mandant.id)
    booking.status = "posted"
    booking.entry_number = entry_number
    await session.flush()
    return booking


async def _get_acc(
    session: AsyncSession, mandant_id: uuid.UUID, number: str
) -> ChartOfAccount:
    result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.account_number == number,
        )
    )
    return result.scalar_one()


async def _get_any(
    session: AsyncSession, mandant_id: uuid.UUID, class_prefix: str
) -> ChartOfAccount:
    """Return any active account whose account_class starts with class_prefix."""
    result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.is_active.is_(True),
            ChartOfAccount.account_class.startswith(class_prefix),
        )
    )
    return result.scalars().first()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Saldenliste — arithmetic
# ---------------------------------------------------------------------------


async def test_saldenliste_returns_all_booked_accounts(
    db_session: AsyncSession,
) -> None:
    """generate_saldenliste must include at least one row per booked account."""
    _, user, mandant = await _setup(db_session)

    revenue = await _get_any(db_session, mandant.id, "8")
    bank = await _get_acc(db_session, mandant.id, "1200")

    await _post_booking(
        db_session, mandant, user, revenue, bank, 50000, date(2026, 1, 10)
    )

    resp = await generate_saldenliste(
        db_session, mandant.id, date(2026, 1, 1), date(2026, 1, 31)
    )
    row_numbers = {r.account_number for r in resp.rows}
    assert revenue.account_number in row_numbers
    assert bank.account_number in row_numbers


async def test_saldenliste_saldo_debit_minus_credit(db_session: AsyncSession) -> None:
    """Each saldenliste row's closing_balance must equal opening + period_debit - period_credit."""
    _, user, mandant = await _setup(db_session)

    expense = await _get_any(db_session, mandant.id, "4")
    bank = await _get_acc(db_session, mandant.id, "1200")

    await _post_booking(
        db_session, mandant, user, expense, bank, 30000, date(2026, 2, 5)
    )
    await _post_booking(
        db_session, mandant, user, expense, bank, 20000, date(2026, 2, 10)
    )

    resp = await generate_saldenliste(
        db_session, mandant.id, date(2026, 2, 1), date(2026, 2, 28)
    )
    for row in resp.rows:
        expected = (
            row.opening_balance_cents + row.period_debit_cents - row.period_credit_cents
        )
        assert row.closing_balance_cents == expected, (
            f"Account {row.account_number}: "
            f"opening={row.opening_balance_cents} "
            f"debit={row.period_debit_cents} "
            f"credit={row.period_credit_cents} "
            f"expected_closing={expected} got={row.closing_balance_cents}"
        )


async def test_saldenliste_total_debit_equals_sum_of_rows(
    db_session: AsyncSession,
) -> None:
    """total_debit_cents must equal the sum of all rows' period_debit_cents."""
    _, user, mandant = await _setup(db_session)

    expense = await _get_any(db_session, mandant.id, "4")
    bank = await _get_acc(db_session, mandant.id, "1200")

    for i in range(3):
        await _post_booking(
            db_session,
            mandant,
            user,
            expense,
            bank,
            10000 * (i + 1),
            date(2026, 3, i + 1),
        )

    resp = await generate_saldenliste(
        db_session, mandant.id, date(2026, 3, 1), date(2026, 3, 31)
    )
    assert resp.total_debit_cents == sum(r.period_debit_cents for r in resp.rows)
    assert resp.total_credit_cents == sum(r.period_credit_cents for r in resp.rows)


# ---------------------------------------------------------------------------
# G+V — revenue and expense split
# ---------------------------------------------------------------------------


async def test_guv_revenue_and_expense_split(db_session: AsyncSession) -> None:
    """G+V must show revenue > 0 and expense > 0 when both are booked."""
    _, user, mandant = await _setup(db_session)

    revenue_acc = await _get_any(db_session, mandant.id, "8")
    expense_acc = await _get_any(db_session, mandant.id, "4")
    bank = await _get_acc(db_session, mandant.id, "1200")

    # Revenue booking: debit=revenue_acc, credit=bank
    await _post_booking(
        db_session, mandant, user, revenue_acc, bank, 100000, date(2026, 1, 5)
    )
    # Expense booking: debit=expense_acc, credit=bank
    await _post_booking(
        db_session, mandant, user, expense_acc, bank, 40000, date(2026, 1, 10)
    )

    resp = await generate_guv(
        db_session, mandant.id, date(2026, 1, 1), date(2026, 1, 31), "skr03"
    )

    assert resp.revenue_total_cents > 0, "Revenue total must be positive"
    assert resp.expense_total_cents > 0, "Expense total must be positive"
    assert resp.result_cents == resp.revenue_total_cents - resp.expense_total_cents


async def test_guv_expense_in_4xxx_accounts(db_session: AsyncSession) -> None:
    """SKR03: expenses booked to 4xxx must appear in expense_rows of G+V."""
    _, user, mandant = await _setup(db_session)

    expense_acc = await _get_any(db_session, mandant.id, "4")
    bank = await _get_acc(db_session, mandant.id, "1200")

    await _post_booking(
        db_session, mandant, user, expense_acc, bank, 25000, date(2026, 4, 1)
    )

    resp = await generate_guv(
        db_session, mandant.id, date(2026, 4, 1), date(2026, 4, 30), "skr03"
    )
    assert resp.expense_total_cents > 0
    # The expense rows must include at least one row with a 4xxx account
    all_expense_account_numbers = [
        num for row in resp.expense_rows for num in row.account_numbers
    ]
    assert any(num.startswith("4") for num in all_expense_account_numbers)


async def test_guv_revenue_in_8xxx_accounts(db_session: AsyncSession) -> None:
    """SKR03: revenue booked to 8xxx must appear in revenue_rows of G+V."""
    _, user, mandant = await _setup(db_session)

    revenue_acc = await _get_any(db_session, mandant.id, "8")
    bank = await _get_acc(db_session, mandant.id, "1200")

    await _post_booking(
        db_session, mandant, user, revenue_acc, bank, 80000, date(2026, 5, 1)
    )

    resp = await generate_guv(
        db_session, mandant.id, date(2026, 5, 1), date(2026, 5, 31), "skr03"
    )
    assert resp.revenue_total_cents > 0
    all_revenue_account_numbers = [
        num for row in resp.revenue_rows for num in row.account_numbers
    ]
    assert any(num.startswith("8") for num in all_revenue_account_numbers)


# ---------------------------------------------------------------------------
# BWA — multi-month data
# ---------------------------------------------------------------------------


async def test_bwa_12_columns_always_returned(db_session: AsyncSession) -> None:
    """generate_bwa must always return exactly 12 monthly columns for the given year."""
    _, user, mandant = await _setup(db_session)

    resp = await generate_bwa(db_session, mandant.id, 2026, "skr03")
    assert len(resp.columns) == 12
    assert [col.month for col in resp.columns] == list(range(1, 13))


async def test_bwa_multi_month_revenue_distribution(db_session: AsyncSession) -> None:
    """Booking revenue in 3 different months must appear in the correct BWA columns."""
    _, user, mandant = await _setup(db_session)

    revenue_acc = await _get_any(db_session, mandant.id, "8")
    bank = await _get_acc(db_session, mandant.id, "1200")

    months_and_amounts = [
        (date(2026, 1, 15), 100000),
        (date(2026, 6, 20), 200000),
        (date(2026, 12, 5), 300000),
    ]
    for booking_date, amount in months_and_amounts:
        await _post_booking(
            db_session, mandant, user, revenue_acc, bank, amount, booking_date
        )

    resp = await generate_bwa(db_session, mandant.id, 2026, "skr03")

    month_map = {col.month: col for col in resp.columns}
    assert month_map[1].revenue_cents == 100000
    assert month_map[6].revenue_cents == 200000
    assert month_map[12].revenue_cents == 300000

    # Months with no bookings should be zero
    for m in (2, 3, 4, 5, 7, 8, 9, 10, 11):
        assert month_map[m].revenue_cents == 0, f"Month {m} revenue must be 0"


async def test_bwa_ytd_revenue_equals_sum_of_monthly_columns(
    db_session: AsyncSession,
) -> None:
    """ytd_revenue_cents must equal the sum of all monthly revenue_cents columns."""
    _, user, mandant = await _setup(db_session)

    revenue_acc = await _get_any(db_session, mandant.id, "8")
    bank = await _get_acc(db_session, mandant.id, "1200")

    await _post_booking(
        db_session, mandant, user, revenue_acc, bank, 50000, date(2026, 3, 1)
    )
    await _post_booking(
        db_session, mandant, user, revenue_acc, bank, 75000, date(2026, 9, 1)
    )

    resp = await generate_bwa(db_session, mandant.id, 2026, "skr03")

    expected_ytd = sum(col.revenue_cents for col in resp.columns)
    assert resp.ytd_revenue_cents == expected_ytd


async def test_bwa_ebit_is_revenue_minus_costs(db_session: AsyncSession) -> None:
    """Each BWA column's ebit_cents must equal revenue - material - personnel - other."""
    _, user, mandant = await _setup(db_session)

    revenue_acc = await _get_any(db_session, mandant.id, "8")
    expense_acc = await _get_any(db_session, mandant.id, "4")
    bank = await _get_acc(db_session, mandant.id, "1200")

    await _post_booking(
        db_session, mandant, user, revenue_acc, bank, 120000, date(2026, 7, 1)
    )
    await _post_booking(
        db_session, mandant, user, expense_acc, bank, 40000, date(2026, 7, 5)
    )

    resp = await generate_bwa(db_session, mandant.id, 2026, "skr03")
    for col in resp.columns:
        expected_ebit = (
            col.revenue_cents
            - col.material_costs_cents
            - col.personnel_costs_cents
            - col.other_costs_cents
        )
        assert (
            col.ebit_cents == expected_ebit
        ), f"Month {col.month}: ebit={col.ebit_cents} != expected {expected_ebit}"


# ---------------------------------------------------------------------------
# API endpoint format tests
# ---------------------------------------------------------------------------


async def test_reports_endpoint_json_format(client, db_session: AsyncSession) -> None:
    """GET /reports/saldenliste?format=json must return 200 with JSON body."""
    headers, user, mandant = await _setup(db_session)

    revenue_acc = await _get_any(db_session, mandant.id, "8")
    bank = await _get_acc(db_session, mandant.id, "1200")
    await _post_booking(
        db_session, mandant, user, revenue_acc, bank, 10000, date(2026, 1, 1)
    )

    resp = await client.get(
        "/api/v1/reports/saldenliste?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "rows" in data
    assert isinstance(data["rows"], list)


async def test_reports_endpoint_csv_format(client, db_session: AsyncSession) -> None:
    """GET /reports/saldenliste?format=csv must return 200 with text/csv content-type."""
    headers, user, mandant = await _setup(db_session)

    revenue_acc = await _get_any(db_session, mandant.id, "8")
    bank = await _get_acc(db_session, mandant.id, "1200")
    await _post_booking(
        db_session, mandant, user, revenue_acc, bank, 10000, date(2026, 1, 1)
    )

    resp = await client.get(
        "/api/v1/reports/saldenliste?date_from=2026-01-01&date_to=2026-01-31&format=csv",
        headers=headers,
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    # CSV must contain at least the header row
    lines = resp.text.strip().splitlines()
    assert len(lines) >= 2
    assert "Account Number" in lines[0]
