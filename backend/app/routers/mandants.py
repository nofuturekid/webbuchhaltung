import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import AccessTokenResponse
from app.schemas.mandant import MandantCreate, MandantResponse, MandantUpdate
from app.services.mandant import (
    create_mandant,
    get_mandant_for_user,
    issue_mandant_token,
    list_mandants,
    update_mandant,
)

router = APIRouter(prefix="/mandants", tags=["mandants"])


@router.get("", response_model=list[MandantResponse])
async def list_(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[MandantResponse]:
    return await list_mandants(session, current_user.id)  # type: ignore[return-value]


@router.post("", response_model=MandantResponse, status_code=201)
async def create(
    body: MandantCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MandantResponse:
    return await create_mandant(session, body, current_user.id)  # type: ignore[return-value]


@router.get("/{mandant_id}", response_model=MandantResponse)
async def get(
    mandant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MandantResponse:
    return await get_mandant_for_user(session, mandant_id, current_user.id)  # type: ignore[return-value]


@router.patch("/{mandant_id}", response_model=MandantResponse)
async def patch(
    mandant_id: uuid.UUID,
    body: MandantUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MandantResponse:
    return await update_mandant(session, mandant_id, current_user.id, body)  # type: ignore[return-value]


@router.post("/{mandant_id}/switch", response_model=AccessTokenResponse)
async def switch(
    mandant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    await get_mandant_for_user(session, mandant_id, current_user.id)
    return AccessTokenResponse(
        access_token=issue_mandant_token(current_user.id, mandant_id)
    )
