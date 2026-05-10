import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "purchase_amount_cents > 0",
            name="ck_asset_purchase_amount_positive",
        ),
        CheckConstraint(
            "useful_life_months > 0",
            name="ck_asset_useful_life_positive",
        ),
        UniqueConstraint(
            "mandant_id",
            "asset_number",
            name="uq_asset_mandant_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    asset_number: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    useful_life_months: Mapped[int] = mapped_column(Integer, nullable=False)
    depreciation_method: Mapped[str] = mapped_column(
        String(10), nullable=False, default="linear"
    )
    residual_value_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    disposal_date: Mapped[date | None] = mapped_column(Date)
    disposal_amount_cents: Mapped[int | None] = mapped_column(BigInteger)
    coa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chart_of_accounts.id"), nullable=False
    )
    depreciation_coa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chart_of_accounts.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )


class AssetSequence(Base):
    __tablename__ = "asset_sequences"

    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), primary_key=True
    )
    next_value: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)


class DepreciationSchedule(Base):
    __tablename__ = "depreciation_schedules"
    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "period_year",
            "period_month",
            name="uq_depreciation_schedule_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cumulative_depreciation_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    net_book_value_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bookings.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
