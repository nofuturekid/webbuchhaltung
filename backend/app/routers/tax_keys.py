from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.account import TaxKeyResponse
from app.services.account import get_tax_key, list_tax_keys

router = APIRouter(prefix="/tax-keys", tags=["tax-keys"])


@router.get("", response_model=list[TaxKeyResponse])
async def list_(session: AsyncSession = Depends(get_db)) -> list[TaxKeyResponse]:
    return await list_tax_keys(session)  # type: ignore[return-value]


@router.get("/{code}", response_model=TaxKeyResponse)
async def get(code: int, session: AsyncSession = Depends(get_db)) -> TaxKeyResponse:
    return await get_tax_key(session, code)  # type: ignore[return-value]
