import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.models.user import User
from app.schemas.reports import (
    BWAResponse,
    BilanzResponse,
    EURResponse,
    GuvResponse,
    KontoauszugResponse,
    SaldenlisteResponse,
)
from app.services.reports import (
    _get_mandant_skr_variant,
    generate_bilanz,
    generate_bwa,
    generate_eur,
    generate_guv,
    generate_kontoauszug,
    generate_saldenliste,
    saldenliste_to_csv,
)

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


@router.get("/saldenliste", response_model=SaldenlisteResponse)
async def saldenliste(
    date_from: date = Query(...),
    date_to: date = Query(...),
    format: str = Query("json", pattern="^(json|csv)$"),
    _current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> SaldenlisteResponse | Response:
    resp = await generate_saldenliste(session, mandant_id, date_from, date_to)
    if format == "csv":
        csv_bytes = saldenliste_to_csv(resp)
        filename = f"saldenliste-{date_from}-{date_to}.csv"
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    return resp


@router.get("/bilanz", response_model=BilanzResponse)
async def bilanz(
    as_of_date: date = Query(...),
    _current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BilanzResponse:
    skr_variant = await _get_mandant_skr_variant(session, mandant_id)
    return await generate_bilanz(session, mandant_id, as_of_date, skr_variant)


@router.get("/guv", response_model=GuvResponse)
async def guv(
    date_from: date = Query(...),
    date_to: date = Query(...),
    _current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> GuvResponse:
    skr_variant = await _get_mandant_skr_variant(session, mandant_id)
    return await generate_guv(session, mandant_id, date_from, date_to, skr_variant)


@router.get("/bwa", response_model=BWAResponse)
async def bwa(
    year: int = Query(...),
    _current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BWAResponse:
    skr_variant = await _get_mandant_skr_variant(session, mandant_id)
    return await generate_bwa(session, mandant_id, year, skr_variant)
