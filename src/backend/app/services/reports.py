import csv
import io
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.account import ChartOfAccount
from app.models.asset import Asset, DepreciationSchedule
from app.models.booking import Booking
from app.models.mandant import Mandant
from app.schemas.reports import (
    BWAColumn,
    BWAResponse,
    BilanzResponse,
    BilanzSection,
    EURLineItem,
    EURResponse,
    GuvResponse,
    GuvRow,
    KontoauszugLine,
    KontoauszugResponse,
    SaldenlisteResponse,
    SaldenlisteRow,
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


# ---------------------------------------------------------------------------
# Saldenliste (Trial Balance)
# ---------------------------------------------------------------------------


async def generate_saldenliste(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> SaldenlisteResponse:
    """Generate a trial balance for all accounts in the given date range."""
    # Load all active accounts for this mandant
    accs_result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.is_active == True,  # noqa: E712
        )
    )
    accounts = accs_result.scalars().all()
    account_by_id: dict[uuid.UUID, ChartOfAccount] = {a.id: a for a in accounts}
    account_ids = list(account_by_id.keys())

    if not account_ids:
        return SaldenlisteResponse(
            date_from=date_from,
            date_to=date_to,
            rows=[],
            total_debit_cents=0,
            total_credit_cents=0,
        )

    # Opening debit aggregation: coa_id bookings before date_from
    opening_debit_q = await session.execute(
        select(Booking.coa_id, func.sum(Booking.amount_cents))
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.coa_id.in_(account_ids),
            Booking.date_booking < date_from,
        )
        .group_by(Booking.coa_id)
    )
    opening_debit: dict[uuid.UUID, int] = {
        row[0]: int(row[1]) for row in opening_debit_q.all()
    }

    # Opening credit aggregation: counter_coa_id bookings before date_from
    opening_credit_q = await session.execute(
        select(Booking.counter_coa_id, func.sum(Booking.amount_cents))
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.counter_coa_id.in_(account_ids),
            Booking.date_booking < date_from,
        )
        .group_by(Booking.counter_coa_id)
    )
    opening_credit: dict[uuid.UUID, int] = {
        row[0]: int(row[1]) for row in opening_credit_q.all()
    }

    # Period debit: coa_id bookings within range
    period_debit_q = await session.execute(
        select(Booking.coa_id, func.sum(Booking.amount_cents))
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.coa_id.in_(account_ids),
            Booking.date_booking >= date_from,
            Booking.date_booking <= date_to,
        )
        .group_by(Booking.coa_id)
    )
    period_debit: dict[uuid.UUID, int] = {
        row[0]: int(row[1]) for row in period_debit_q.all()
    }

    # Period credit: counter_coa_id bookings within range
    period_credit_q = await session.execute(
        select(Booking.counter_coa_id, func.sum(Booking.amount_cents))
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.counter_coa_id.in_(account_ids),
            Booking.date_booking >= date_from,
            Booking.date_booking <= date_to,
        )
        .group_by(Booking.counter_coa_id)
    )
    period_credit: dict[uuid.UUID, int] = {
        row[0]: int(row[1]) for row in period_credit_q.all()
    }

    rows: list[SaldenlisteRow] = []
    total_debit = 0
    total_credit = 0

    for acc in sorted(accounts, key=lambda a: a.account_number):
        op_d = opening_debit.get(acc.id, 0)
        op_c = opening_credit.get(acc.id, 0)
        opening = op_d - op_c

        p_debit = period_debit.get(acc.id, 0)
        p_credit = period_credit.get(acc.id, 0)

        closing = opening + p_debit - p_credit

        if opening == 0 and p_debit == 0 and p_credit == 0:
            continue

        rows.append(
            SaldenlisteRow(
                account_number=acc.account_number,
                account_name=acc.name,
                opening_balance_cents=opening,
                period_debit_cents=p_debit,
                period_credit_cents=p_credit,
                closing_balance_cents=closing,
            )
        )
        total_debit += p_debit
        total_credit += p_credit

    return SaldenlisteResponse(
        date_from=date_from,
        date_to=date_to,
        rows=rows,
        total_debit_cents=total_debit,
        total_credit_cents=total_credit,
    )


def saldenliste_to_csv(resp: SaldenlisteResponse) -> bytes:
    """Serialize a SaldenlisteResponse to CSV bytes."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Account Number",
            "Account Name",
            "Opening Balance (cents)",
            "Period Debit (cents)",
            "Period Credit (cents)",
            "Closing Balance (cents)",
        ]
    )
    for row in resp.rows:
        writer.writerow(
            [
                row.account_number,
                row.account_name,
                row.opening_balance_cents,
                row.period_debit_cents,
                row.period_credit_cents,
                row.closing_balance_cents,
            ]
        )
    writer.writerow([])
    writer.writerow(
        [
            "",
            "Totals",
            "",
            resp.total_debit_cents,
            resp.total_credit_cents,
            "",
        ]
    )
    return buf.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Bilanz (Balance Sheet, HGB §266)
# ---------------------------------------------------------------------------


async def _account_balance_as_of(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    account_ids: list[uuid.UUID],
    as_of_date: date,
) -> dict[uuid.UUID, int]:
    """Compute net balance (debit - credit) for each account up to as_of_date."""
    if not account_ids:
        return {}

    debit_q = await session.execute(
        select(Booking.coa_id, func.sum(Booking.amount_cents))
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.coa_id.in_(account_ids),
            Booking.date_booking <= as_of_date,
        )
        .group_by(Booking.coa_id)
    )
    debit_map: dict[uuid.UUID, int] = {row[0]: int(row[1]) for row in debit_q.all()}

    credit_q = await session.execute(
        select(Booking.counter_coa_id, func.sum(Booking.amount_cents))
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.counter_coa_id.in_(account_ids),
            Booking.date_booking <= as_of_date,
        )
        .group_by(Booking.counter_coa_id)
    )
    credit_map: dict[uuid.UUID, int] = {row[0]: int(row[1]) for row in credit_q.all()}

    result: dict[uuid.UUID, int] = {}
    for acc_id in account_ids:
        result[acc_id] = debit_map.get(acc_id, 0) - credit_map.get(acc_id, 0)
    return result


async def generate_bilanz(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    as_of_date: date,
    skr_variant: str,
) -> BilanzResponse:
    """Generate a simplified balance sheet (Bilanz) as of a given date."""
    # Load all active accounts
    accs_result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.is_active == True,  # noqa: E712
        )
    )
    accounts = accs_result.scalars().all()

    # Partition accounts into Anlagevermögen (0xxx), Umlaufvermögen (1xxx),
    # Eigenkapital (0xxx with "Eigenkapital" in name or account_number 0800-0899),
    # and Verbindlichkeiten
    anlagev_accs = [a for a in accounts if a.account_class.startswith("0")]
    umlaufv_accs = [a for a in accounts if a.account_class.startswith("1")]

    # Eigenkapital: 0xxx accounts containing "eigenkapital" (case-insensitive)
    # or in number range 0800-0899
    eigenkapital_accs = [
        a
        for a in anlagev_accs
        if "eigenkapital" in a.name.lower() or ("0800" <= a.account_number <= "0899")
    ]
    # Verbindlichkeiten: accounts for AP and liabilities
    if skr_variant == "skr04":
        verbindlichkeiten_accs = [
            a for a in accounts if a.account_class.startswith("3")
        ]
    else:  # skr03 default
        verbindlichkeiten_accs = [
            a
            for a in umlaufv_accs
            if a.account_number >= "1600" and a.account_number <= "1799"
        ]

    all_acc_ids = [a.id for a in accounts]
    balances = await _account_balance_as_of(
        session, mandant_id, all_acc_ids, as_of_date
    )

    # --- Anlagevermögen: use DepreciationSchedule if available, else purchase amount ---
    assets_result = await session.execute(
        select(Asset).where(
            Asset.mandant_id == mandant_id,
            Asset.status == "active",
            Asset.purchase_date <= as_of_date,
        )
    )
    asset_objects = assets_result.scalars().all()
    asset_ids = [a.id for a in asset_objects]

    # Get latest posted depreciation schedule row per asset
    latest_nbv: dict[uuid.UUID, int] = {}
    if asset_ids:
        sched_result = await session.execute(
            select(DepreciationSchedule)
            .where(
                DepreciationSchedule.mandant_id == mandant_id,
                DepreciationSchedule.asset_id.in_(asset_ids),
                DepreciationSchedule.booking_id.is_not(None),
            )
            .order_by(
                DepreciationSchedule.asset_id,
                DepreciationSchedule.period_year.desc(),
                DepreciationSchedule.period_month.desc(),
            )
        )
        seen: set[uuid.UUID] = set()
        for sched in sched_result.scalars().all():
            if sched.asset_id not in seen:
                latest_nbv[sched.asset_id] = sched.net_book_value_cents
                seen.add(sched.asset_id)

    anlagev_total = 0
    for asset in asset_objects:
        if asset.id in latest_nbv:
            anlagev_total += latest_nbv[asset.id]
        else:
            # No posted depreciation: approximate with purchase - residual
            anlagev_total += asset.purchase_amount_cents - asset.residual_value_cents

    # Umlaufvermögen: sum of 1xxx account balances (excluding Verbindlichkeiten)
    verbindlichkeiten_ids = {a.id for a in verbindlichkeiten_accs}
    umlaufv_total = sum(
        balances.get(a.id, 0) for a in umlaufv_accs if a.id not in verbindlichkeiten_ids
    )

    aktiva_total = anlagev_total + umlaufv_total
    aktiva: list[BilanzSection] = [
        BilanzSection(label="A. Anlagevermögen", amount_cents=anlagev_total),
        BilanzSection(label="B. Umlaufvermögen", amount_cents=umlaufv_total),
    ]

    # PASSIVA
    eigenkapital_total = sum(balances.get(a.id, 0) for a in eigenkapital_accs)
    verbindlichkeiten_total = sum(balances.get(a.id, 0) for a in verbindlichkeiten_accs)
    passiva_total = eigenkapital_total + verbindlichkeiten_total
    passiva: list[BilanzSection] = [
        BilanzSection(label="A. Eigenkapital", amount_cents=eigenkapital_total),
        BilanzSection(
            label="B. Verbindlichkeiten", amount_cents=verbindlichkeiten_total
        ),
    ]

    imbalance = abs(aktiva_total - passiva_total)
    return BilanzResponse(
        as_of_date=as_of_date,
        aktiva=aktiva,
        passiva=passiva,
        aktiva_total_cents=aktiva_total,
        passiva_total_cents=passiva_total,
        balanced=(imbalance == 0),
        imbalance_cents=imbalance,
    )


# ---------------------------------------------------------------------------
# G+V (Gewinn- und Verlustrechnung)
# ---------------------------------------------------------------------------


def _is_revenue_account(account: ChartOfAccount, skr_variant: str) -> bool:
    """Return True if this account contributes to revenues in G+V."""
    if skr_variant == "skr04":
        # SKR04: 4xxx accounts that are revenue (USt, steuerfrei) — not expense/USt-payable
        return account.account_class.startswith("4") and account.tax_type in (
            "USt",
            "steuerfrei",
        )
    # SKR03: 8xxx accounts are revenues
    return account.account_class.startswith("8")


def _is_expense_account(account: ChartOfAccount, skr_variant: str) -> bool:
    """Return True if this account contributes to expenses in G+V."""
    if skr_variant == "skr04":
        return account.account_class.startswith(("5", "6", "7"))
    # SKR03: 4xxx, 5xxx, 6xxx, 7xxx are expenses
    return account.account_class.startswith(("4", "5", "6", "7"))


async def _period_net_by_account(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    account_ids: list[uuid.UUID],
    date_from: date,
    date_to: date,
) -> dict[uuid.UUID, int]:
    """Compute net movement (debit - credit) per account in the period."""
    if not account_ids:
        return {}

    debit_q = await session.execute(
        select(Booking.coa_id, func.sum(Booking.amount_cents))
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.coa_id.in_(account_ids),
            Booking.date_booking >= date_from,
            Booking.date_booking <= date_to,
        )
        .group_by(Booking.coa_id)
    )
    debit_map: dict[uuid.UUID, int] = {row[0]: int(row[1]) for row in debit_q.all()}

    credit_q = await session.execute(
        select(Booking.counter_coa_id, func.sum(Booking.amount_cents))
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.counter_coa_id.in_(account_ids),
            Booking.date_booking >= date_from,
            Booking.date_booking <= date_to,
        )
        .group_by(Booking.counter_coa_id)
    )
    credit_map: dict[uuid.UUID, int] = {row[0]: int(row[1]) for row in credit_q.all()}

    result: dict[uuid.UUID, int] = {}
    for acc_id in account_ids:
        result[acc_id] = debit_map.get(acc_id, 0) - credit_map.get(acc_id, 0)
    return result


async def generate_guv(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    date_from: date,
    date_to: date,
    skr_variant: str,
) -> GuvResponse:
    """Generate a profit and loss statement (G+V) for the given date range."""
    accs_result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.is_active == True,  # noqa: E712
        )
    )
    accounts = accs_result.scalars().all()

    revenue_accs = [a for a in accounts if _is_revenue_account(a, skr_variant)]
    expense_accs = [a for a in accounts if _is_expense_account(a, skr_variant)]

    revenue_ids = [a.id for a in revenue_accs]
    expense_ids = [a.id for a in expense_accs]

    revenue_net = await _period_net_by_account(
        session, mandant_id, revenue_ids, date_from, date_to
    )
    expense_net = await _period_net_by_account(
        session, mandant_id, expense_ids, date_from, date_to
    )

    # Group by first digit of account_number
    rev_groups: dict[str, list[ChartOfAccount]] = defaultdict(list)
    for acc in revenue_accs:
        rev_groups[acc.account_number[0]].append(acc)

    exp_groups: dict[str, list[ChartOfAccount]] = defaultdict(list)
    for acc in expense_accs:
        exp_groups[acc.account_number[0]].append(acc)

    revenue_rows: list[GuvRow] = []
    revenue_total = 0
    for digit, accs in sorted(rev_groups.items()):
        group_total = sum(revenue_net.get(a.id, 0) for a in accs)
        if group_total == 0:
            continue
        revenue_rows.append(
            GuvRow(
                label=f"Erlöse {digit}xxx",
                account_numbers=[
                    a.account_number
                    for a in sorted(accs, key=lambda x: x.account_number)
                ],
                amount_cents=group_total,
            )
        )
        revenue_total += group_total

    expense_rows: list[GuvRow] = []
    expense_total = 0
    for digit, accs in sorted(exp_groups.items()):
        group_total = sum(expense_net.get(a.id, 0) for a in accs)
        if group_total == 0:
            continue
        expense_rows.append(
            GuvRow(
                label=f"Aufwand {digit}xxx",
                account_numbers=[
                    a.account_number
                    for a in sorted(accs, key=lambda x: x.account_number)
                ],
                amount_cents=group_total,
            )
        )
        expense_total += group_total

    return GuvResponse(
        date_from=date_from,
        date_to=date_to,
        revenue_rows=revenue_rows,
        expense_rows=expense_rows,
        revenue_total_cents=revenue_total,
        expense_total_cents=expense_total,
        result_cents=revenue_total - expense_total,
    )


# ---------------------------------------------------------------------------
# BWA (Betriebswirtschaftliche Auswertung)
# ---------------------------------------------------------------------------


def _classify_bwa(account: ChartOfAccount, skr_variant: str) -> str | None:
    """Return BWA category: 'revenue', 'material', 'personnel', 'other', or None."""
    num = account.account_number
    cls = account.account_class

    if _is_revenue_account(account, skr_variant):
        return "revenue"

    if skr_variant == "skr04":
        # Material costs: 5xxx
        if cls.startswith("5"):
            return "material"
        # Personnel costs: 62xx
        if cls.startswith("6") and num.startswith("62"):
            return "personnel"
        # Other costs: remaining 6xxx, 7xxx expense accounts
        if cls.startswith(("6", "7")):
            return "other"
    else:
        # SKR03
        # Material costs: 3xxx
        if cls.startswith("3"):
            return "material"
        # Personnel costs: 40xx-43xx
        if cls.startswith("4") and "4000" <= num <= "4399":
            return "personnel"
        # Other costs: remaining 4xxx, 5xxx, 6xxx, 7xxx
        if cls.startswith(("4", "5", "6", "7")):
            return "other"

    return None


async def generate_bwa(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    year: int,
    skr_variant: str,
) -> BWAResponse:
    """Generate a monthly management report (BWA) for the given year."""
    accs_result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.is_active == True,  # noqa: E712
        )
    )
    accounts = accs_result.scalars().all()

    # Classify each account
    acc_categories: dict[uuid.UUID, str] = {}
    for acc in accounts:
        cat = _classify_bwa(acc, skr_variant)
        if cat:
            acc_categories[acc.id] = cat

    classified_ids = list(acc_categories.keys())
    if not classified_ids:
        empty_columns = [
            BWAColumn(
                year=year,
                month=m,
                revenue_cents=0,
                material_costs_cents=0,
                personnel_costs_cents=0,
                other_costs_cents=0,
                ebit_cents=0,
            )
            for m in range(1, 13)
        ]
        return BWAResponse(
            year=year, columns=empty_columns, ytd_revenue_cents=0, ytd_ebit_cents=0
        )

    # Debit side: GROUP BY month, coa_id
    month_expr = func.extract("month", Booking.date_booking)
    debit_q = await session.execute(
        select(Booking.coa_id, month_expr, func.sum(Booking.amount_cents))
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.coa_id.in_(classified_ids),
            func.extract("year", Booking.date_booking) == year,
        )
        .group_by(Booking.coa_id, month_expr)
    )
    # credit side
    credit_q = await session.execute(
        select(Booking.counter_coa_id, month_expr, func.sum(Booking.amount_cents))
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.counter_coa_id.in_(classified_ids),
            func.extract("year", Booking.date_booking) == year,
        )
        .group_by(Booking.counter_coa_id, month_expr)
    )

    # month_data[month][category] = net_cents
    month_data: dict[int, dict[str, int]] = {
        m: {"revenue": 0, "material": 0, "personnel": 0, "other": 0}
        for m in range(1, 13)
    }

    for acc_id, month_raw, total in debit_q.all():
        month = int(month_raw)
        cat = acc_categories.get(acc_id)
        if cat:
            month_data[month][cat] += int(total)

    for acc_id, month_raw, total in credit_q.all():
        month = int(month_raw)
        cat = acc_categories.get(acc_id)
        if cat:
            month_data[month][cat] -= int(total)

    columns: list[BWAColumn] = []
    ytd_revenue = 0
    ytd_ebit = 0

    for m in range(1, 13):
        md = month_data[m]
        revenue = md["revenue"]
        material = md["material"]
        personnel = md["personnel"]
        other = md["other"]
        ebit = revenue - material - personnel - other
        ytd_revenue += revenue
        ytd_ebit += ebit
        columns.append(
            BWAColumn(
                year=year,
                month=m,
                revenue_cents=revenue,
                material_costs_cents=material,
                personnel_costs_cents=personnel,
                other_costs_cents=other,
                ebit_cents=ebit,
            )
        )

    return BWAResponse(
        year=year,
        columns=columns,
        ytd_revenue_cents=ytd_revenue,
        ytd_ebit_cents=ytd_ebit,
    )


async def _get_mandant_skr_variant(session: AsyncSession, mandant_id: uuid.UUID) -> str:
    """Fetch skr_variant for the given mandant."""
    result = await session.execute(
        select(Mandant.skr_variant).where(Mandant.id == mandant_id)
    )
    variant = result.scalar_one_or_none()
    if not variant:
        raise NotFoundError(f"Mandant {mandant_id} not found.")
    return variant
