import calendar
import uuid
from datetime import date

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import (
    AccountLookupError,
    AssetAlreadyDisposedError,
    AssetImmutableError,
    ConflictError,
    NotFoundError,
    PeriodLockedError,
)
from app.models.account import ChartOfAccount
from app.models.asset import Asset, DepreciationSchedule
from app.models.booking import Booking
from app.models.mandant import Mandant
from app.schemas.asset import (
    AssetCreate,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
    DisposeAssetRequest,
)
from app.services.audit import write_audit
from app.services.booking import get_next_entry_number
from app.services.period import get_or_create_period


async def _get_account_id(
    session: AsyncSession, mandant_id: uuid.UUID, account_number: str
) -> uuid.UUID:
    result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.mandant_id == mandant_id,
            ChartOfAccount.account_number == account_number,
        )
    )
    coa = result.scalar_one_or_none()
    if coa is None:
        raise AccountLookupError(f"Account {account_number} not found for mandant.")
    return coa.id


async def generate_asset_number(
    session: AsyncSession, mandant_id: uuid.UUID, purchase_year: int
) -> str:
    """Generate the next unique asset number for a mandant atomically.

    Format: AV-{year}-{n:03d}, e.g. AV-2026-001. Mirrors get_next_entry_number().
    """
    conn = await session.connection()
    dialect_name = conn.dialect.name

    if dialect_name == "postgresql":
        result = await session.execute(
            text(
                "INSERT INTO asset_sequences (mandant_id, next_value) VALUES (:id, 2) "
                "ON CONFLICT (mandant_id) DO UPDATE "
                "SET next_value = asset_sequences.next_value + 1 "
                "RETURNING next_value - 1"
            ),
            {"id": str(mandant_id)},
        )
        n = int(result.scalar_one())
    elif dialect_name in ("mysql", "mariadb"):
        await session.execute(
            text(
                "INSERT INTO asset_sequences (mandant_id, next_value) "
                "VALUES (:id, LAST_INSERT_ID(1)) "
                "ON DUPLICATE KEY UPDATE next_value = LAST_INSERT_ID(next_value + 1)"
            ),
            {"id": str(mandant_id)},
        )
        result = await session.execute(text("SELECT LAST_INSERT_ID()"))
        n = int(result.scalar_one())
    else:
        raise NotImplementedError(
            f"Unsupported dialect for asset number sequencing: {dialect_name}"
        )

    return f"AV-{purchase_year}-{n:03d}"


def compute_depreciation_schedule(asset: Asset) -> list[dict]:
    """Compute the full depreciation schedule for an asset. Pure function — no DB access."""
    if asset.depreciation_method == "none":
        return []

    total_to_depreciate = asset.purchase_amount_cents - asset.residual_value_cents
    if total_to_depreciate <= 0 or asset.useful_life_months <= 0:
        return []

    monthly_base = total_to_depreciate // asset.useful_life_months
    remainder = total_to_depreciate % asset.useful_life_months

    # First period = first full calendar month after purchase_date
    pd = asset.purchase_date
    if pd.month == 12:
        first_year = pd.year + 1
        first_month = 1
    else:
        first_year = pd.year
        first_month = pd.month + 1

    entries: list[dict] = []
    cumulative = 0
    year = first_year
    month = first_month

    for i in range(asset.useful_life_months):
        is_last = i == asset.useful_life_months - 1
        amount = monthly_base + remainder if is_last else monthly_base
        cumulative += amount

        entries.append(
            {
                "period_year": year,
                "period_month": month,
                "amount_cents": amount,
                "cumulative_depreciation_cents": cumulative,
                "net_book_value_cents": asset.purchase_amount_cents - cumulative,
            }
        )

        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return entries


async def _regenerate_schedule(session: AsyncSession, asset: Asset) -> None:
    """Delete unposted schedule rows and rebuild. Posted rows are never touched."""
    await session.execute(
        delete(DepreciationSchedule).where(
            DepreciationSchedule.asset_id == asset.id,
            DepreciationSchedule.booking_id.is_(None),
        )
    )

    posted_result = await session.execute(
        select(DepreciationSchedule).where(
            DepreciationSchedule.asset_id == asset.id,
            DepreciationSchedule.booking_id.is_not(None),
        )
    )
    posted_periods: set[tuple[int, int]] = {
        (row.period_year, row.period_month) for row in posted_result.scalars().all()
    }

    full_schedule = compute_depreciation_schedule(asset)

    for entry in full_schedule:
        key = (entry["period_year"], entry["period_month"])
        if key in posted_periods:
            continue
        session.add(
            DepreciationSchedule(
                id=uuid.uuid4(),
                asset_id=asset.id,
                mandant_id=asset.mandant_id,
                period_year=entry["period_year"],
                period_month=entry["period_month"],
                amount_cents=entry["amount_cents"],
                cumulative_depreciation_cents=entry["cumulative_depreciation_cents"],
                net_book_value_cents=entry["net_book_value_cents"],
            )
        )


async def create_asset(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: AssetCreate,
) -> Asset:
    asset_number = await generate_asset_number(
        session, mandant_id, data.purchase_date.year
    )
    asset = Asset(
        mandant_id=mandant_id,
        created_by=user_id,
        asset_number=asset_number,
        name=data.name,
        description=data.description,
        purchase_date=data.purchase_date,
        purchase_amount_cents=data.purchase_amount_cents,
        useful_life_months=data.useful_life_months,
        depreciation_method=data.depreciation_method,
        residual_value_cents=data.residual_value_cents,
        coa_id=data.coa_id,
        depreciation_coa_id=data.depreciation_coa_id,
        status="active",
    )
    session.add(asset)
    await session.flush()

    await _regenerate_schedule(session, asset)
    await session.flush()

    await write_audit(
        session,
        table_name="assets",
        record_id=asset.id,
        action="insert",
        change_summary={"asset_number": asset_number, "name": data.name},
        mandant_id=mandant_id,
        user_id=user_id,
    )
    await session.refresh(asset)
    return asset


async def list_assets(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> AssetListResponse:
    base_q = select(Asset).where(Asset.mandant_id == mandant_id)
    total = int(
        (
            await session.execute(select(func.count()).select_from(base_q.subquery()))
        ).scalar_one()
    )

    assets = list(
        (
            await session.execute(
                base_q.order_by(Asset.purchase_date.desc(), Asset.asset_number)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    response_items: list[AssetResponse] = []
    for asset in assets:
        last_posted = (
            await session.execute(
                select(DepreciationSchedule)
                .where(
                    DepreciationSchedule.asset_id == asset.id,
                    DepreciationSchedule.booking_id.is_not(None),
                )
                .order_by(
                    DepreciationSchedule.period_year.desc(),
                    DepreciationSchedule.period_month.desc(),
                )
                .limit(1)
            )
        ).scalar_one_or_none()

        item = AssetResponse.model_validate(asset)
        if last_posted is not None:
            item.total_depreciated_cents = last_posted.cumulative_depreciation_cents
            item.net_book_value_cents = last_posted.net_book_value_cents
        else:
            item.total_depreciated_cents = 0
            item.net_book_value_cents = asset.purchase_amount_cents
        response_items.append(item)

    return AssetListResponse(
        items=response_items, total=total, page=page, page_size=page_size
    )


async def get_asset(
    session: AsyncSession, asset_id: uuid.UUID, mandant_id: uuid.UUID
) -> Asset:
    result = await session.execute(
        select(Asset).where(Asset.id == asset_id, Asset.mandant_id == mandant_id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise NotFoundError(f"Asset {asset_id} not found.")
    return asset


async def update_asset(
    session: AsyncSession,
    asset_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: AssetUpdate,
) -> Asset:
    asset = await get_asset(session, asset_id, mandant_id)

    immutable_fields = {"purchase_amount_cents", "useful_life_months"}
    if immutable_fields & set(data.model_dump(exclude_unset=True).keys()):
        posted_check = (
            await session.execute(
                select(DepreciationSchedule)
                .where(
                    DepreciationSchedule.asset_id == asset.id,
                    DepreciationSchedule.booking_id.is_not(None),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if posted_check is not None:
            raise AssetImmutableError()

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)

    await _regenerate_schedule(session, asset)
    await session.flush()

    await write_audit(
        session,
        table_name="assets",
        record_id=asset.id,
        action="update",
        change_summary=data.model_dump(exclude_unset=True),
        mandant_id=mandant_id,
        user_id=user_id,
    )
    await session.refresh(asset)
    return asset


async def get_depreciation_schedule(
    session: AsyncSession, asset_id: uuid.UUID, mandant_id: uuid.UUID
) -> list[DepreciationSchedule]:
    await get_asset(session, asset_id, mandant_id)
    result = await session.execute(
        select(DepreciationSchedule)
        .where(DepreciationSchedule.asset_id == asset_id)
        .order_by(DepreciationSchedule.period_year, DepreciationSchedule.period_month)
    )
    return list(result.scalars().all())


async def book_depreciation(
    session: AsyncSession,
    asset_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    period_year: int,
    period_month: int,
) -> Booking:
    """Create and post a depreciation booking for a single period."""
    asset = await get_asset(session, asset_id, mandant_id)

    schedule = (
        await session.execute(
            select(DepreciationSchedule).where(
                DepreciationSchedule.asset_id == asset_id,
                DepreciationSchedule.period_year == period_year,
                DepreciationSchedule.period_month == period_month,
            )
        )
    ).scalar_one_or_none()
    if schedule is None:
        raise NotFoundError(
            f"No depreciation schedule entry for period {period_year}/{period_month:02d}."
        )

    if schedule.booking_id is not None:
        raise ConflictError(
            f"Depreciation for {period_year}/{period_month:02d} is already booked."
        )

    period = await get_or_create_period(session, mandant_id, period_year, period_month)
    if period.status in ("locked", "archived"):
        raise PeriodLockedError()

    last_day = calendar.monthrange(period_year, period_month)[1]
    booking_date = date(period_year, period_month, last_day)
    booking_text = f"AfA {asset.name} {period_year}/{period_month:02d}"[:60]

    booking = Booking(
        mandant_id=mandant_id,
        booking_type="entry",
        date_booking=booking_date,
        amount_cents=schedule.amount_cents,
        currency="EUR",
        notes=booking_text,
        coa_id=asset.depreciation_coa_id,
        counter_coa_id=asset.coa_id,
        status="draft",
        created_by=user_id,
    )
    session.add(booking)
    await session.flush()

    entry_number = await get_next_entry_number(session, mandant_id)
    booking.status = "posted"
    booking.entry_number = entry_number

    await write_audit(
        session,
        table_name="bookings",
        record_id=booking.id,
        action="update",
        change_summary={
            "transition": "draft→posted",
            "status": ["draft", "posted"],
            "entry_number": [None, entry_number],
        },
        mandant_id=mandant_id,
        user_id=user_id,
    )
    await session.flush()

    schedule.booking_id = booking.id

    await write_audit(
        session,
        table_name="assets",
        record_id=asset.id,
        action="update",
        change_summary={
            "depreciation_booked": f"{period_year}/{period_month:02d}",
            "booking_id": str(booking.id),
        },
        mandant_id=mandant_id,
        user_id=user_id,
    )
    await session.flush()
    await session.refresh(booking)
    return booking


async def dispose_asset(
    session: AsyncSession,
    asset_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: DisposeAssetRequest,
) -> Asset:
    """Dispose an asset with GoBD-clean double-entry write-off bookings."""
    asset = await get_asset(session, asset_id, mandant_id)

    if asset.status != "active":
        raise AssetAlreadyDisposedError()

    last_posted = (
        await session.execute(
            select(DepreciationSchedule)
            .where(
                DepreciationSchedule.asset_id == asset.id,
                DepreciationSchedule.booking_id.is_not(None),
            )
            .order_by(
                DepreciationSchedule.period_year.desc(),
                DepreciationSchedule.period_month.desc(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    net_book_value = (
        last_posted.net_book_value_cents
        if last_posted is not None
        else asset.purchase_amount_cents
    )

    mandant = (
        await session.execute(select(Mandant).where(Mandant.id == mandant_id))
    ).scalar_one()

    # SKR04 uses 1800 (Bankkonten), SKR03/07 use 1200 (Bank)
    bank_account_number = "1800" if mandant.skr_variant == "skr04" else "1200"
    loss_account_number = "4830" if mandant.skr_variant == "skr04" else "4855"
    gain_account_number = "2310" if mandant.skr_variant == "skr04" else "2680"

    booking_date = data.disposal_date
    period = await get_or_create_period(
        session, mandant_id, booking_date.year, booking_date.month
    )
    if period.status in ("locked", "archived"):
        raise PeriodLockedError()

    disposal_note = f"Abgang {asset.name}"[:60]

    async def _post_booking(
        coa_id: uuid.UUID, counter_coa_id: uuid.UUID, amount: int
    ) -> Booking:
        b = Booking(
            mandant_id=mandant_id,
            booking_type="entry",
            date_booking=booking_date,
            amount_cents=amount,
            currency="EUR",
            notes=disposal_note,
            coa_id=coa_id,
            counter_coa_id=counter_coa_id,
            status="draft",
            created_by=user_id,
        )
        session.add(b)
        await session.flush()
        en = await get_next_entry_number(session, mandant_id)
        b.status = "posted"
        b.entry_number = en
        await write_audit(
            session,
            table_name="bookings",
            record_id=b.id,
            action="update",
            change_summary={"transition": "draft→posted", "entry_number": [None, en]},
            mandant_id=mandant_id,
            user_id=user_id,
        )
        await session.flush()
        return b

    if data.disposal_amount_cents > 0:
        bank_id = await _get_account_id(session, mandant_id, bank_account_number)
        await _post_booking(bank_id, asset.coa_id, data.disposal_amount_cents)

    net_remaining = net_book_value - data.disposal_amount_cents
    if net_remaining > 0:
        loss_id = await _get_account_id(session, mandant_id, loss_account_number)
        await _post_booking(loss_id, asset.coa_id, net_remaining)
    elif net_remaining < 0:
        gain_id = await _get_account_id(session, mandant_id, gain_account_number)
        await _post_booking(asset.coa_id, gain_id, abs(net_remaining))

    asset.status = "disposed"
    asset.disposal_date = data.disposal_date
    asset.disposal_amount_cents = data.disposal_amount_cents

    await write_audit(
        session,
        table_name="assets",
        record_id=asset.id,
        action="update",
        change_summary={
            "status": ["active", "disposed"],
            "disposal_date": str(data.disposal_date),
            "disposal_amount_cents": data.disposal_amount_cents,
        },
        mandant_id=mandant_id,
        user_id=user_id,
    )
    await session.flush()
    await session.refresh(asset)
    return asset
