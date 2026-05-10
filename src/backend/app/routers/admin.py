import uuid
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.errors import ForbiddenError, NotFoundError
from app.models.period import AuditLog
from app.models.user import User, UserMandant
from app.schemas.auth import UserResponse
from app.services.auth import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    is_active: bool | None = None


class UserMandantAssign(BaseModel):
    user_id: uuid.UUID
    role: Literal["admin", "bookkeeper", "readonly"] = "bookkeeper"


async def _require_admin(
    mandant_id: uuid.UUID,
    current_user: User,
    session: AsyncSession,
) -> None:
    result = await session.execute(
        select(UserMandant).where(
            UserMandant.user_id == current_user.id,
            UserMandant.mandant_id == mandant_id,
            UserMandant.role == "admin",
        )
    )
    if not result.scalar_one_or_none():
        raise ForbiddenError("Admin role required.")


async def _require_any_admin(
    current_user: User,
    session: AsyncSession,
) -> None:
    result = await session.execute(
        select(UserMandant).where(
            UserMandant.user_id == current_user.id,
            UserMandant.role == "admin",
        )
    )
    if not result.scalar_one_or_none():
        raise ForbiddenError("Admin role required.")


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    await _require_any_admin(current_user, session)
    admin_mandant_ids = select(UserMandant.mandant_id).where(
        UserMandant.user_id == current_user.id,
        UserMandant.role == "admin",
    )
    result = await session.execute(
        select(User)
        .join(UserMandant, UserMandant.user_id == User.id)
        .where(UserMandant.mandant_id.in_(admin_mandant_ids))
        .distinct()
    )
    return list(result.scalars().all())  # type: ignore[return-value]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    await _require_any_admin(current_user, session)
    user = User(email=body.email, hashed_password=hash_password(body.password))
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    await _require_any_admin(current_user, session)
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User {user_id} not found.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.flush()
    await session.refresh(user)
    return user


@router.post("/mandants/{mandant_id}/users")
async def assign_user_to_mandant(
    mandant_id: uuid.UUID,
    body: UserMandantAssign,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await _require_admin(mandant_id, current_user, session)
    user_result = await session.execute(select(User).where(User.id == body.user_id))
    if not user_result.scalar_one_or_none():
        raise NotFoundError(f"User {body.user_id} not found.")
    link = UserMandant(user_id=body.user_id, mandant_id=mandant_id, role=body.role)
    session.add(link)
    await session.flush()
    return {"message": "User assigned."}


@router.get("/audit-log")
async def get_audit_log(
    table: str | None = Query(default=None),
    action: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    filters = [AuditLog.mandant_id == mandant_id]
    if table:
        filters.append(AuditLog.table_name == table)
    if action:
        filters.append(AuditLog.action == action)
    if date_from:
        filters.append(
            AuditLog.changed_at
            >= datetime(
                date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc
            )
        )
    if date_to:
        filters.append(
            AuditLog.changed_at
            < datetime(
                date_to.year, date_to.month, date_to.day + 1, tzinfo=timezone.utc
            )
        )

    where_clause = and_(*filters)

    total_result = await session.execute(
        select(func.count()).select_from(AuditLog).where(where_clause)
    )
    total: int = total_result.scalar_one()

    rows_result = await session.execute(
        select(AuditLog)
        .where(where_clause)
        .order_by(AuditLog.changed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = rows_result.scalars().all()

    items = [
        {
            "id": str(row.id),
            "table_name": row.table_name,
            "record_id": str(row.record_id),
            "action": row.action,
            "change_summary": row.change_summary,
            "changed_at": row.changed_at.isoformat(),
            "user_id": str(row.user_id) if row.user_id else None,
            "mandant_id": str(row.mandant_id) if row.mandant_id else None,
        }
        for row in rows
    ]

    return {"items": items, "total": total, "page": page, "page_size": page_size}
