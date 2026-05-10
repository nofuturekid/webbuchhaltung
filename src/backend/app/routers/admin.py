import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.errors import ForbiddenError, NotFoundError
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
