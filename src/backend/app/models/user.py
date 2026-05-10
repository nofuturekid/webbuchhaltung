import uuid

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserMandant(Base):
    __tablename__ = "user_mandants"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandants.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(
        SAEnum("admin", "bookkeeper", "readonly", name="user_role_enum"),
        default="bookkeeper",
        nullable=False,
    )
