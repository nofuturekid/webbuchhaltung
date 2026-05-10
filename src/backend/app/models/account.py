import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ChartOfAccount(Base, TimestampMixin):
    __tablename__ = "chart_of_accounts"
    __table_args__ = (
        UniqueConstraint("mandant_id", "account_number", name="uq_coa_mandant_number"),
        CheckConstraint(
            "private_share_percent BETWEEN 0 AND 100", name="ck_coa_private_share"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), nullable=False
    )
    account_number: Mapped[str] = mapped_column(String(4), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_class: Mapped[str] = mapped_column(String(10), nullable=False)
    tax_type: Mapped[str | None] = mapped_column(String(50))
    skr_variant: Mapped[str] = mapped_column(
        SAEnum("skr03", "skr04", "skr07", "custom", name="skr_source_enum"),
        nullable=False,
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    private_share_percent: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TaxKey(Base):
    __tablename__ = "tax_keys"

    code: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    tax_type: Mapped[str] = mapped_column(
        SAEnum(
            "USt", "VSt", "steuerfrei", "§13b", "keine", "UStfrei", name="tax_type_enum"
        ),
        nullable=False,
    )
