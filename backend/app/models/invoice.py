import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    street: Mapped[str | None] = mapped_column(String(200))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(2), default="DE", nullable=False)
    vat_id: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(254))


class InvoiceSequence(Base):
    __tablename__ = "invoice_sequences"
    __table_args__ = (
        UniqueConstraint("mandant_id", name="uq_invoice_sequence_mandant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    prefix: Mapped[str] = mapped_column(String(20), default="RE", nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    year_reset: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_reset_year: Mapped[int | None] = mapped_column(Integer)


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        SAEnum("draft", "issued", "cancelled", name="invoice_status_enum"),
        default="draft",
        nullable=False,
    )
    issue_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    net_total_cents: Mapped[int | None] = mapped_column(BigInteger)
    vat_total_cents: Mapped[int | None] = mapped_column(BigInteger)
    gross_total_cents: Mapped[int | None] = mapped_column(BigInteger)
    notes: Mapped[str | None] = mapped_column(Text)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bookings.id", use_alter=True, name="fk_invoices_booking_id"),
    )


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("invoices.id"), nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20))
    unit_price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    net_total_cents: Mapped[int | None] = mapped_column(BigInteger)
    vat_amount_cents: Mapped[int | None] = mapped_column(BigInteger)


class InvoiceTemplate(Base):
    __tablename__ = "invoice_templates"
    __table_args__ = (
        UniqueConstraint("mandant_id", name="uq_invoice_template_mandant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    logo_path: Mapped[str | None] = mapped_column(String(500))
    primary_color: Mapped[str] = mapped_column(
        String(7), default="#000000", nullable=False
    )
    font_family: Mapped[str] = mapped_column(
        String(100), default="Arial, sans-serif", nullable=False
    )
    header_text: Mapped[str | None] = mapped_column(Text)
    footer_text: Mapped[str | None] = mapped_column(Text)
    payment_terms_text: Mapped[str] = mapped_column(
        String(200), default="Zahlbar innerhalb von 14 Tagen", nullable=False
    )
    custom_html_template: Mapped[str | None] = mapped_column(Text)
    use_custom_template: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
