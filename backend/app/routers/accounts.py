import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_mandant_id
from app.schemas.account import (
    AccountBalanceResponse,
    AccountCreate,
    AccountResponse,
    AccountUpdate,
)
from app.services.account import (
    create_custom_account,
    deactivate_account,
    get_account,
    get_account_balance,
    list_accounts,
    update_account,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_(
    account_class: str | None = Query(None),
    is_active: bool | None = Query(None),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list[AccountResponse]:
    return await list_accounts(session, mandant_id, account_class, is_active)  # type: ignore[return-value]


@router.post("", response_model=AccountResponse, status_code=201)
async def create(
    body: AccountCreate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> AccountResponse:
    return await create_custom_account(session, mandant_id, body)  # type: ignore[return-value]


@router.get("/{account_id}", response_model=AccountResponse)
async def get(
    account_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> AccountResponse:
    return await get_account(session, account_id, mandant_id)  # type: ignore[return-value]


@router.patch("/{account_id}", response_model=AccountResponse)
async def update(
    account_id: uuid.UUID,
    body: AccountUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> AccountResponse:
    return await update_account(session, account_id, mandant_id, body)  # type: ignore[return-value]


@router.delete("/{account_id}", status_code=204)
async def delete(
    account_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> None:
    await deactivate_account(session, account_id, mandant_id)


@router.get("/{account_id}/balance", response_model=AccountBalanceResponse)
async def balance(
    account_id: uuid.UUID,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> AccountBalanceResponse:
    return await get_account_balance(
        session, account_id, mandant_id, date_from, date_to
    )
