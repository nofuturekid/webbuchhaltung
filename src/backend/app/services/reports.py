import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.schemas.reports import (
    EURLineItem,
    EURResponse,
    KontoauszugLine,
    KontoauszugResponse,
)


async def generate_eur(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> EURResponse:
    result = await session.execute(
        select(Booking, ChartOfAccount)
        .join(ChartOfAccount, Booking.coa_id == ChartOfAccount.id)
        .where(
            Booking.mandant_id == mandant_id,
            ChartOfAccount.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.date_booking >= date_from,
            Booking.date_booking <= date_to,
        )
        .order_by(ChartOfAccount.account_number)
    )
    rows = result.all()

    aggregates: dict[str, dict] = {}
    for booking, account in rows:
        key = account.account_number
        if key not in aggregates:
            aggregates[key] = {
                "account": account,
                "gross_cents": 0,
                "tax_cents": 0,
                "vst_19_cents": 0,
                "vst_7_cents": 0,
            }
        booking_tax = booking.tax_amount_cents or 0
        aggregates[key]["gross_cents"] += booking.amount_cents
        aggregates[key]["tax_cents"] += booking_tax
        if account.account_class.startswith(("4", "5", "6")):
            if booking.tax_rate == Decimal("0.19"):
                aggregates[key]["vst_19_cents"] += booking_tax
            elif booking.tax_rate == Decimal("0.07"):
                aggregates[key]["vst_7_cents"] += booking_tax

    items = []
    betriebseinnahmen = 0
    betriebsausgaben = 0
    ust_cents = 0
    vst_19_cents = 0
    vst_7_cents = 0

    for acct_num, agg in aggregates.items():
        coa: ChartOfAccount = agg["account"]
        gross = agg["gross_cents"]
        tax = agg["tax_cents"]
        net = gross - tax
        private = (net * coa.private_share_percent) // 100
        reportable = net - private

        if coa.account_class.startswith("8"):
            betriebseinnahmen += reportable
            ust_cents += tax
        elif coa.account_class.startswith(("4", "5", "6")):
            betriebsausgaben += reportable
            vst_19_cents += agg["vst_19_cents"]
            vst_7_cents += agg["vst_7_cents"]

        items.append(
            EURLineItem(
                account_number=acct_num,
                account_name=coa.name,
                gross_cents=gross,
                tax_cents=tax,
                net_cents=net,
                private_deduction_cents=private,
                reportable_cents=reportable,
            )
        )

    return EURResponse(
        date_from=str(date_from),
        date_to=str(date_to),
        betriebseinnahmen_cents=betriebseinnahmen,
        betriebsausgaben_cents=betriebsausgaben,
        ust_cents=ust_cents,
        vst_19_cents=vst_19_cents,
        vst_7_cents=vst_7_cents,
        items=items,
    )


async def generate_kontoauszug(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    account_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> KontoauszugResponse:
    acc_result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.id == account_id,
            ChartOfAccount.mandant_id == mandant_id,
        )
    )
    account = acc_result.scalar_one_or_none()
    if not account:
        raise NotFoundError(f"Account {account_id} not found.")

    opening_result = await session.execute(
        select(Booking)
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            (Booking.coa_id == account_id) | (Booking.counter_coa_id == account_id),
            Booking.date_booking < date_from,
        )
        .order_by(Booking.date_booking, Booking.entry_number)
    )
    opening_balance = sum(
        b.amount_cents if b.coa_id == account_id else -b.amount_cents
        for b in opening_result.scalars().all()
    )

    result = await session.execute(
        select(Booking)
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            (Booking.coa_id == account_id) | (Booking.counter_coa_id == account_id),
            Booking.date_booking >= date_from,
            Booking.date_booking <= date_to,
        )
        .order_by(Booking.date_booking, Booking.entry_number)
    )
    bookings = list(result.scalars().all())

    lines = []
    running_balance = opening_balance
    for b in bookings:
        debit = b.amount_cents if b.coa_id == account_id else 0
        credit = b.amount_cents if b.counter_coa_id == account_id else 0
        running_balance += debit - credit
        lines.append(
            KontoauszugLine(
                booking_id=b.id,
                date_booking=str(b.date_booking),
                document_number=b.document_number,
                notes=b.notes,
                debit_cents=debit,
                credit_cents=credit,
                running_balance_cents=running_balance,
                entry_number=b.entry_number,
                status=b.status,
            )
        )

    return KontoauszugResponse(
        account_id=account_id,
        account_number=account.account_number,
        account_name=account.name,
        date_from=str(date_from),
        date_to=str(date_to),
        opening_balance_cents=opening_balance,
        closing_balance_cents=running_balance,
        lines=lines,
    )
