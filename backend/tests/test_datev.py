import uuid
from datetime import date

from sqlalchemy import select

from app.models.account import ChartOfAccount
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.account import seed_skr_for_mandant
from app.services.auth import create_access_token, hash_password
from app.services.datev import _datev_date, _format_amount, _tax_key_to_bu


async def _setup_posted_booking(
    session, client
) -> tuple[dict[str, str], Mandant, ChartOfAccount, ChartOfAccount]:
    user = User(email=f"d{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(
        name="DATEV GmbH",
        skr_variant="skr03",
        datev_beraternummer="70000",
        datev_mandantennummer="12345",
    )
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    accs = (
        (
            await session.execute(
                select(ChartOfAccount)
                .where(ChartOfAccount.mandant_id == mandant.id)
                .limit(2)
            )
        )
        .scalars()
        .all()
    )
    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-15",
            "amount_cents": 119000,
            "document_number": "RE2026-001",
            "notes": "Testbuchung",
            "coa_id": str(accs[0].id),
            "counter_coa_id": str(accs[1].id),
        },
        headers=headers,
    )
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    return headers, mandant, accs[0], accs[1]


def test_format_amount() -> None:
    assert _format_amount(119000) == "1190,00"
    assert _format_amount(100) == "1,00"
    assert _format_amount(50) == "0,50"


def test_datev_date_format() -> None:
    assert _datev_date(date(2026, 1, 15)) == "1501"
    assert _datev_date(date(2026, 12, 31)) == "3112"


def test_tax_key_mapping() -> None:
    assert _tax_key_to_bu(9) == "9"
    assert _tax_key_to_bu(10) == "10"
    assert _tax_key_to_bu(None) == ""
    assert _tax_key_to_bu(99) == ""


async def test_export_returns_cp1252_csv(client, db_session):
    headers, mandant, acc1, acc2 = await _setup_posted_booking(db_session, client)
    resp = await client.post(
        "/api/v1/datev/export",
        json={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.content.decode("cp1252")
    assert "EXTF" in content
    assert "1190,00" in content


async def test_export_soll_haben_kennzeichen(client, db_session):
    headers, mandant, acc1, acc2 = await _setup_posted_booking(db_session, client)
    resp = await client.post(
        "/api/v1/datev/export",
        json={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )
    lines = resp.content.decode("cp1252").splitlines()
    data_line = lines[2]  # 0=header1, 1=header2, 2=first data row
    fields = data_line.split(";")
    assert fields[1] == "S"
    assert fields[6] == acc1.account_number
    assert fields[7] == acc2.account_number


async def test_export_document_number_truncated_to_12(client, db_session):
    headers, mandant, acc1, acc2 = await _setup_posted_booking(db_session, client)
    resp = await client.post(
        "/api/v1/datev/export",
        json={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )
    lines = resp.content.decode("cp1252").splitlines()
    data_line = lines[2]
    fields = data_line.split(";")
    assert len(fields[10]) <= 12


async def test_export_only_posted_entry_bookings(client, db_session):
    headers, mandant, acc1, acc2 = await _setup_posted_booking(db_session, client)
    await client.post(
        "/api/v1/bookings",
        json={
            "date_booking": "2026-01-20",
            "amount_cents": 50000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        },
        headers=headers,
    )
    resp = await client.post(
        "/api/v1/datev/export",
        json={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers,
    )
    lines = [
        line
        for line in resp.content.decode("cp1252").splitlines()
        if line and not line.startswith('"EXTF') and not line.startswith("Umsatz")
    ]
    assert len(lines) == 1


async def test_datev_mandant_isolation(client, db_session):
    headers1, mandant1, acc1, acc2 = await _setup_posted_booking(db_session, client)
    # Second mandant with no bookings
    user2 = User(email=f"iso{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    db_session.add(user2)
    mandant2 = Mandant(name="ISO DATEV GmbH", skr_variant="skr03")
    db_session.add(mandant2)
    await db_session.flush()
    db_session.add(UserMandant(user_id=user2.id, mandant_id=mandant2.id, role="admin"))
    await db_session.flush()
    headers2 = {"Authorization": f"Bearer {create_access_token(user2.id, mandant2.id)}"}
    resp = await client.post(
        "/api/v1/datev/export",
        json={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=headers2,
    )
    assert resp.status_code == 200
    lines = [
        line
        for line in resp.content.decode("cp1252").splitlines()
        if line and not line.startswith('"EXTF') and not line.startswith("Umsatz")
    ]
    assert len(lines) == 0
