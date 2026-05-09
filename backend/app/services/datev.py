import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.models.mandant import Mandant


def _format_amount(cents: int) -> str:
    return f"{cents // 100},{cents % 100:02d}"


def _datev_date(d: date) -> str:
    return d.strftime("%d%m")


def _datev_leistungsdatum(d: date | None) -> str:
    if d is None:
        return ""
    return d.strftime("%d%m%Y")


def _tax_key_to_bu(tax_key_code: int | None) -> str:
    if tax_key_code in (9, 10):
        return str(tax_key_code)
    return ""


async def generate_datev_export(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> bytes:
    mandant_result = await session.execute(
        select(Mandant).where(Mandant.id == mandant_id)
    )
    mandant = mandant_result.scalar_one()

    result = await session.execute(
        select(Booking, ChartOfAccount.account_number.label("coa_number"))
        .join(ChartOfAccount, Booking.coa_id == ChartOfAccount.id)
        .where(
            Booking.mandant_id == mandant_id,
            ChartOfAccount.mandant_id == mandant_id,
            Booking.booking_type == "entry",
            Booking.status == "posted",
            Booking.date_booking >= date_from,
            Booking.date_booking <= date_to,
        )
        .order_by(Booking.entry_number)
    )
    rows = result.all()

    counter_ids = [r.Booking.counter_coa_id for r in rows if r.Booking.counter_coa_id]
    counter_map: dict[uuid.UUID, str] = {}
    if counter_ids:
        counter_result = await session.execute(
            select(ChartOfAccount.id, ChartOfAccount.account_number).where(
                ChartOfAccount.mandant_id == mandant_id,
                ChartOfAccount.id.in_(counter_ids),
            )
        )
        counter_map = {row.id: row.account_number for row in counter_result}

    now = datetime.now(timezone.utc)
    fiscal_start_date = date(now.year, mandant.fiscal_year_start, 1)
    fiscal_end_date = date(
        fiscal_start_date.year + (0 if mandant.fiscal_year_start == 1 else 1),
        mandant.fiscal_year_start,
        1,
    ) - timedelta(days=1)
    wj_anfang = fiscal_start_date.strftime("%Y%m%d")
    wj_ende = fiscal_end_date.strftime("%Y%m%d")

    beraternr = mandant.datev_beraternummer or "70000"
    mandantennr = mandant.datev_mandantennummer or "99999"

    lines: list[str] = []

    header1 = (
        f'"EXTF";700;21;"Buchungsstapel";5;'
        f'{now.strftime("%Y%m%d%H%M%S%f")[:20]};;'
        f'"{beraternr}";"{mandantennr}";'
        f'{mandant.fiscal_year_start};12;'
        f'"{wj_anfang}";"{wj_ende}";'
        f'"WebBuchhaltung";;1;0;0;0;;1;EUR;;;'
    )
    lines.append(header1)

    lines.append(
        "Umsatz (ohne Soll/Haben-Kz);Soll/Haben-Kennzeichen;WKZ Umsatz;Kurs;"
        "Basis-Umsatz;WKZ Basis-Umsatz;Konto;Gegenkonto (ohne BU-Schlüssel);"
        "BU-Schlüssel;Belegdatum;Belegfeld 1;Belegfeld 2;Skonto;Buchungstext"
    )

    for row in rows:
        b: Booking = row.Booking
        coa_number: str = row.coa_number
        counter_number = (
            counter_map.get(b.counter_coa_id, "") if b.counter_coa_id else ""
        )

        fields = [
            _format_amount(b.amount_cents),
            "S",
            b.currency,
            "",
            "",
            "",
            coa_number,
            counter_number,
            _tax_key_to_bu(b.tax_key_code),
            _datev_date(b.date_booking),
            (b.document_number or "")[:12],
            "",
            "",
            (b.notes or "")[:60],
        ]
        lines.append(";".join(fields))

    content = "\r\n".join(lines) + "\r\n"
    return content.encode("cp1252", errors="replace")
