import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import UnauthorizedError
from app.models.user import User
from app.services.auth import decode_token

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated.")
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type.")
    result = await session.execute(
        select(User).where(User.id == uuid.UUID(payload["sub"]))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")
    return user


def get_mandant_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> uuid.UUID:
    if credentials is None:
        raise UnauthorizedError("Not authenticated.")
    payload = decode_token(credentials.credentials)
    mandant_id = payload.get("mandant_id")
    if not mandant_id:
        raise UnauthorizedError("No Mandant selected. Use /mandants/{id}/switch first.")
    return uuid.UUID(mandant_id)
