import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    __table_args__ = (
        UniqueConstraint("mandant_id", "iban", name="uq_bank_account_mandant_iban"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    iban: Mapped[str] = mapped_column(String(34), nullable=False)
    bic: Mapped[str | None] = mapped_column(String(11))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    __table_args__ = (
        CheckConstraint("amount_cents != 0", name="ck_bank_transaction_amount_nonzero"),
        UniqueConstraint(
            "bank_account_id", "source_ref", name="uq_bank_transaction_source_ref"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[date | None] = mapped_column(Date)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    purpose: Mapped[str | None] = mapped_column(String(500))
    counterpart_name: Mapped[str | None] = mapped_column(String(200))
    counterpart_iban: Mapped[str | None] = mapped_column(String(34))
    source_format: Mapped[str] = mapped_column(String(10), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unmatched")
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bookings.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
