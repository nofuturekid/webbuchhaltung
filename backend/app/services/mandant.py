import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.mandant import Mandant
from app.models.user import UserMandant
from app.schemas.mandant import MandantCreate, MandantUpdate
from app.services.auth import create_access_token


async def get_mandant_for_user(
    session: AsyncSession, mandant_id: uuid.UUID, user_id: uuid.UUID
) -> Mandant:
    result = await session.execute(
        select(Mandant)
        .join(UserMandant, UserMandant.mandant_id == Mandant.id)
        .where(Mandant.id == mandant_id, UserMandant.user_id == user_id)
    )
    mandant = result.scalar_one_or_none()
    if not mandant:
        raise NotFoundError(f"Mandant {mandant_id} not found.")
    return mandant


async def list_mandants(session: AsyncSession, user_id: uuid.UUID) -> list[Mandant]:
    result = await session.execute(
        select(Mandant)
        .join(UserMandant, UserMandant.mandant_id == Mandant.id)
        .where(UserMandant.user_id == user_id, Mandant.is_active.is_(True))
    )
    return list(result.scalars().all())


async def create_mandant(
    session: AsyncSession, data: MandantCreate, user_id: uuid.UUID
) -> Mandant:
    mandant = Mandant(**data.model_dump())
    session.add(mandant)
    await session.flush()
    link = UserMandant(user_id=user_id, mandant_id=mandant.id, role="admin")
    session.add(link)
    await session.flush()
    await session.refresh(mandant)
    return mandant


async def update_mandant(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MandantUpdate,
) -> Mandant:
    mandant = await get_mandant_for_user(session, mandant_id, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(mandant, field, value)
    await session.flush()
    await session.refresh(mandant)
    return mandant


def issue_mandant_token(user_id: uuid.UUID, mandant_id: uuid.UUID) -> str:
    return create_access_token(user_id, mandant_id)
