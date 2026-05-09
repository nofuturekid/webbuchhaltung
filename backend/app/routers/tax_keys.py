from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import NotFoundError
from app.models.account import TaxKey
from app.schemas.account import TaxKeyResponse
from app.services.account import list_tax_keys

router = APIRouter(prefix="/tax-keys", tags=["tax-keys"])


@router.get("", response_model=list[TaxKeyResponse])
async def list_(session: AsyncSession = Depends(get_db)) -> list[TaxKeyResponse]:
    return await list_tax_keys(session)  # type: ignore[return-value]


@router.get("/{code}", response_model=TaxKeyResponse)
async def get(code: int, session: AsyncSession = Depends(get_db)) -> TaxKeyResponse:
    result = await session.execute(select(TaxKey).where(TaxKey.code == code))
    tk = result.scalar_one_or_none()
    if not tk:
        raise NotFoundError(f"TaxKey {code} not found.")
    return tk  # type: ignore[return-value]
