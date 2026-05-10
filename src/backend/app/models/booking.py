import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BookingGroup(Base):
    __tablename__ = "booking_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BookingSequence(Base):
    __tablename__ = "booking_sequences"

    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), primary_key=True
    )
    next_value: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_booking_amount_positive"),
        CheckConstraint(
            "booking_type != 'entry' OR (coa_id IS NOT NULL AND counter_coa_id IS NOT NULL)",
            name="ck_booking_entry_accounts",
        ),
        CheckConstraint(
            "status != 'posted' OR entry_number IS NOT NULL",
            name="ck_booking_posted_has_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    booking_type: Mapped[str] = mapped_column(
        SAEnum("bank", "entry", name="booking_type_enum"), nullable=False
    )
    booking_group_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("booking_groups.id")
    )
    parent_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bookings.id")
    )
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bookings.id")
    )

    date_booking: Mapped[date] = mapped_column(Date, nullable=False)
    date_tax: Mapped[date | None] = mapped_column(Date)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(
        SAEnum("draft", "posted", "reversed", name="booking_status_enum"),
        default="draft",
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String(60))
    entry_number: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # entry type only (NULL for bank)
    coa_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chart_of_accounts.id")
    )
    counter_coa_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chart_of_accounts.id")
    )
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    tax_amount_cents: Mapped[int | None] = mapped_column(BigInteger)
    tax_key_code: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tax_keys.code")
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True)
    )  # FK → contacts (Phase 3)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", use_alter=True, name="fk_bookings_invoice_id"),
    )

    # bank type only (NULL for entry)
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bank_accounts.id")
    )
    recipient_name: Mapped[str | None] = mapped_column(String(255))
    foreign_bank_account: Mapped[str | None] = mapped_column(String(50))
