import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.models.user import User
from app.schemas.reports import EURResponse, KontoauszugResponse
from app.services.reports import generate_eur, generate_kontoauszug

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/eur", response_model=EURResponse)
async def eur(
    date_from: date = Query(...),
    date_to: date = Query(...),
    _current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> EURResponse:
    return await generate_eur(session, mandant_id, date_from, date_to)


@router.get("/account-statement", response_model=KontoauszugResponse)
async def account_statement(
    account_id: uuid.UUID = Query(...),
    date_from: date = Query(...),
    date_to: date = Query(...),
    _current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> KontoauszugResponse:
    return await generate_kontoauszug(
        session, mandant_id, account_id, date_from, date_to
    )
