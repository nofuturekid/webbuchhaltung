from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mandant import Mandant
from app.models.user import User
from app.schemas.mandant import MandantCreate
from app.services.auth import hash_password
from app.services.mandant import create_mandant


async def system_needs_bootstrap(session: AsyncSession) -> bool:
    """Return True if no users exist in the database."""
    result = await session.execute(select(func.count()).select_from(User))
    count: int = result.scalar_one()
    return count == 0


async def bootstrap_first_admin(
    session: AsyncSession,
    email: str,
    password: str,
    mandant_name: str,
    skr_variant: str,
) -> tuple[User, Mandant]:
    """Create the first admin user and their mandant.

    The caller is responsible for committing the session.
    """
    user = User(email=email, hashed_password=hash_password(password))
    session.add(user)
    await session.flush()

    mandant = await create_mandant(
        session,
        MandantCreate(name=mandant_name, skr_variant=skr_variant),  # type: ignore[arg-type]
        user.id,
    )
    return (user, mandant)
