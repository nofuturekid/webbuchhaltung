import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.errors import NotFoundError
from app.models.bank import BankAccount, BankTransaction
from app.models.user import User
from app.schemas.bank import (
    BankAccountCreate,
    BankAccountResponse,
    BankAccountUpdate,
    BankTransactionListResponse,
    BankTransactionResponse,
    CsvColumnMap,
    ImportStatsResponse,
    MatchCandidateResponse,
    MatchRequest,
)
from app.services.bank_import import (
    import_transactions,
    parse_csv_transactions,
    parse_mt940,
)
from app.services.bank_matching import (
    apply_ignore,
    apply_match,
    apply_unmatch,
    find_match_candidates,
    run_auto_matching,
)

router = APIRouter(tags=["bank"])


# ---------------------------------------------------------------------------
# Bank accounts
# ---------------------------------------------------------------------------


@router.get(
    "/bank-accounts/",
    response_model=list[BankAccountResponse],
    summary="List bank accounts",
)
async def list_bank_accounts(
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list[BankAccount]:
    result = await session.execute(
        select(BankAccount).where(BankAccount.mandant_id == mandant_id)
    )
    return list(result.scalars().all())


@router.post(
    "/bank-accounts/",
    response_model=BankAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create bank account",
)
async def create_bank_account(
    payload: BankAccountCreate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BankAccount:
    account = BankAccount(
        mandant_id=mandant_id,
        name=payload.name,
        iban=payload.iban,
        bic=payload.bic,
        currency=payload.currency,
    )
    session.add(account)
    await session.flush()
    await session.refresh(account)
    return account


@router.patch(
    "/bank-accounts/{account_id}",
    response_model=BankAccountResponse,
    summary="Update bank account",
)
async def update_bank_account(
    account_id: uuid.UUID,
    payload: BankAccountUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BankAccount:
    account = await _get_account(session, account_id, mandant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    await session.flush()
    await session.refresh(account)
    return account


@router.delete(
    "/bank-accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate bank account",
)
async def deactivate_bank_account(
    account_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> None:
    account = await _get_account(session, account_id, mandant_id)
    account.is_active = False
    await session.flush()


# ---------------------------------------------------------------------------
# Import endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/bank-accounts/{account_id}/import/mt940",
    response_model=ImportStatsResponse,
    summary="Import MT940 statement",
)
async def import_mt940(
    account_id: uuid.UUID,
    file: UploadFile = File(...),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> ImportStatsResponse:
    account = await _get_account(session, account_id, mandant_id)
    content = await file.read()
    transactions = parse_mt940(content)
    imported, skipped = await import_transactions(
        session, account.id, mandant_id, transactions, "mt940"
    )
    return ImportStatsResponse(imported=imported, skipped=skipped)


@router.post(
    "/bank-accounts/{account_id}/import/csv",
    response_model=ImportStatsResponse,
    summary="Import CSV statement",
)
async def import_csv(
    account_id: uuid.UUID,
    file: UploadFile = File(...),
    date_col: str = Query(
        default="Datum", description="Column name for transaction date"
    ),
    amount_col: str = Query(default="Betrag", description="Column name for amount"),
    purpose_col: str | None = Query(
        default="Verwendungszweck", description="Column name for purpose"
    ),
    counterpart_name_col: str | None = Query(
        default=None, description="Column name for counterpart name"
    ),
    counterpart_iban_col: str | None = Query(
        default=None, description="Column name for counterpart IBAN"
    ),
    date_format: str = Query(default="%d.%m.%Y", description="Date format string"),
    decimal_separator: str = Query(
        default=",", description="Decimal separator (, or .)"
    ),
    encoding: str = Query(default="utf-8-sig", description="File encoding"),
    skip_rows: int = Query(
        default=0, description="Number of header rows to skip after CSV header"
    ),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> ImportStatsResponse:
    account = await _get_account(session, account_id, mandant_id)
    content = await file.read()
    column_map = CsvColumnMap(
        date_col=date_col,
        amount_col=amount_col,
        purpose_col=purpose_col,
        counterpart_name_col=counterpart_name_col,
        counterpart_iban_col=counterpart_iban_col,
        date_format=date_format,
        decimal_separator=decimal_separator,
        encoding=encoding,
        skip_rows=skip_rows,
    )
    transactions = parse_csv_transactions(content, column_map)
    imported, skipped = await import_transactions(
        session, account.id, mandant_id, transactions, "csv"
    )
    return ImportStatsResponse(imported=imported, skipped=skipped)


# ---------------------------------------------------------------------------
# Transaction list
# ---------------------------------------------------------------------------


@router.get(
    "/bank-accounts/{account_id}/transactions",
    response_model=BankTransactionListResponse,
    summary="List transactions",
)
async def list_transactions(
    account_id: uuid.UUID,
    status: str | None = Query(
        default=None, description="Filter by status: unmatched, matched, ignored"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BankTransactionListResponse:
    await _get_account(session, account_id, mandant_id)

    q = select(BankTransaction).where(
        BankTransaction.bank_account_id == account_id,
        BankTransaction.mandant_id == mandant_id,
    )
    if status is not None:
        q = q.where(BankTransaction.status == status)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(count_q)).scalar_one()

    items_result = await session.execute(
        q.order_by(BankTransaction.transaction_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(items_result.scalars().all())

    return BankTransactionListResponse(
        items=items, total=int(total), page=page, page_size=page_size
    )


# ---------------------------------------------------------------------------
# Auto-match
# ---------------------------------------------------------------------------


@router.post(
    "/bank-accounts/{account_id}/auto-match",
    summary="Run automatic matching",
)
async def auto_match(
    account_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    await _get_account(session, account_id, mandant_id)
    matched, remaining = await run_auto_matching(
        session, account_id, mandant_id, current_user.id
    )
    return {"matched": matched, "remaining": remaining}


# ---------------------------------------------------------------------------
# Transaction-level operations
# ---------------------------------------------------------------------------


@router.post(
    "/bank-transactions/{transaction_id}/match",
    response_model=list[MatchCandidateResponse],
    summary="Match transaction to booking",
)
async def match_transaction(
    transaction_id: uuid.UUID,
    payload: MatchRequest,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[MatchCandidateResponse]:
    await apply_match(
        session, transaction_id, payload.booking_id, mandant_id, current_user.id
    )
    # Return updated candidates (will be empty after match)
    candidates = await find_match_candidates(session, transaction_id, mandant_id)
    return [
        MatchCandidateResponse(
            booking_id=c.booking_id,
            booking_date=c.booking_date,
            amount_cents=c.amount_cents,
            description=c.description,
            entry_number=c.entry_number,
            score=c.score,
        )
        for c in candidates
    ]


@router.post(
    "/bank-transactions/{transaction_id}/ignore",
    response_model=BankTransactionResponse,
    summary="Ignore transaction",
)
async def ignore_transaction(
    transaction_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BankTransaction:
    return await apply_ignore(session, transaction_id, mandant_id, current_user.id)


@router.post(
    "/bank-transactions/{transaction_id}/unmatch",
    response_model=BankTransactionResponse,
    summary="Unmatch transaction",
)
async def unmatch_transaction(
    transaction_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BankTransaction:
    return await apply_unmatch(session, transaction_id, mandant_id, current_user.id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_account(
    session: AsyncSession, account_id: uuid.UUID, mandant_id: uuid.UUID
) -> BankAccount:
    account = (
        await session.execute(
            select(BankAccount).where(
                BankAccount.id == account_id,
                BankAccount.mandant_id == mandant_id,
            )
        )
    ).scalar_one_or_none()
    if account is None:
        raise NotFoundError(f"Bank account {account_id} not found.")
    return account
