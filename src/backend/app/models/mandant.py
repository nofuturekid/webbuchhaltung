import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    Integer,
    SmallInteger,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Mandant(Base, TimestampMixin):
    __tablename__ = "mandants"
    __table_args__ = (
        CheckConstraint(
            "fiscal_year_start BETWEEN 1 AND 12", name="ck_mandant_fiscal_year_start"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    steuernummer: Mapped[str | None] = mapped_column(String(50))
    ust_id: Mapped[str | None] = mapped_column(String(20))
    datev_beraternummer: Mapped[str | None] = mapped_column(String(10))
    datev_mandantennummer: Mapped[str | None] = mapped_column(String(10))
    fiscal_year_start: Mapped[int] = mapped_column(Integer, default=1)
    skr_variant: Mapped[str] = mapped_column(
        SAEnum("skr03", "skr04", "skr07", name="skr_variant_enum"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    iban: Mapped[str | None] = mapped_column(String(34))
    bic: Mapped[str | None] = mapped_column(String(11))
    smtp_host: Mapped[str | None] = mapped_column(String(253))
    smtp_port: Mapped[int] = mapped_column(SmallInteger, default=587, nullable=False)
    smtp_user: Mapped[str | None] = mapped_column(String(254))
    smtp_password: Mapped[str | None] = mapped_column(String(500))
    smtp_from: Mapped[str | None] = mapped_column(String(254))
    smtp_from_name: Mapped[str | None] = mapped_column(String(200))
    email_salutation: Mapped[str | None] = mapped_column(String(500))
    email_closing: Mapped[str | None] = mapped_column(String(500))
