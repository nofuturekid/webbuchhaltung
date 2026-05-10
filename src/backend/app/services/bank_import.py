import csv
import io
import uuid
from dataclasses import dataclass
from datetime import date, datetime

import mt940  # from mt-940 PyPI package
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank import BankTransaction
from app.schemas.bank import CsvColumnMap


@dataclass
class RawTransaction:
    transaction_date: date
    value_date: date | None
    amount_cents: int  # negative = debit, positive = credit
    purpose: str | None
    counterpart_name: str | None
    counterpart_iban: str | None
    source_ref: str


def parse_mt940(content: bytes) -> list[RawTransaction]:
    """Parse MT940 SWIFT statement bytes using the mt-940 library.

    Handles multi-bank quirks via mt-940's built-in processors.
    Raises ValueError on malformed content.
    """
    try:
        # Try UTF-8 first, fall back to ISO-8859-1 (common for German banks)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("iso-8859-1")

        transactions = mt940.models.Transactions()
        transactions.parse(text)
    except Exception as exc:
        raise ValueError(f"MT940 parse error: {exc}") from exc

    result: list[RawTransaction] = []
    for i, tx in enumerate(transactions.transactions):
        # Amount: mt940 uses Decimal with sign already applied (C=positive, D=negative)
        amount_obj = tx.data.get("amount")
        if amount_obj is None:
            continue
        # Amount object has .amount attribute (Decimal)
        amount_cents = int(amount_obj.amount * 100)
        if amount_cents == 0:
            continue

        # Purpose from transaction details (:86: field)
        details = tx.data.get("transaction_details", "") or ""
        purpose = details[:500] if details else None

        # Counterpart info (mt940 may parse these from :86: sub-fields)
        counterpart_name = tx.data.get("applicant_name") or tx.data.get("applicant_bin")
        counterpart_iban = tx.data.get("applicant_iban") or tx.data.get(
            "account_identification"
        )

        # Build dedup key from date + amount + position
        tx_date: date = tx.data["date"]
        source_ref = f"{tx_date.isoformat()}:{amount_cents}:{i:04d}"

        result.append(
            RawTransaction(
                transaction_date=tx_date,
                value_date=tx.data.get("value_date"),
                amount_cents=amount_cents,
                purpose=purpose,
                counterpart_name=(
                    str(counterpart_name)[:200] if counterpart_name else None
                ),
                counterpart_iban=(
                    str(counterpart_iban)[:34] if counterpart_iban else None
                ),
                source_ref=source_ref,
            )
        )
    return result


def parse_csv_transactions(
    content: bytes, column_map: CsvColumnMap
) -> list[RawTransaction]:
    """Parse a CSV bank export using user-supplied column mapping.

    Handles German decimal format (1.234,56 → 123456 cents).
    """
    text = content.decode(column_map.encoding)
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    result: list[RawTransaction] = []
    for i, row in enumerate(rows[column_map.skip_rows :]):
        # Date parsing
        date_str = row.get(column_map.date_col, "").strip()
        if not date_str:
            continue
        tx_date = datetime.strptime(date_str, column_map.date_format).date()

        # Amount parsing — handle German format
        amount_str = row.get(column_map.amount_col, "").strip()
        if not amount_str:
            continue
        # Remove thousands separator, replace decimal separator
        if column_map.decimal_separator == ",":
            amount_str = amount_str.replace(".", "").replace(",", ".")
        amount_float = float(amount_str)
        amount_cents = round(amount_float * 100)
        if amount_cents == 0:
            continue

        purpose = None
        if column_map.purpose_col:
            purpose = row.get(column_map.purpose_col, "").strip()[:500] or None

        counterpart_name = None
        if column_map.counterpart_name_col:
            counterpart_name = (
                row.get(column_map.counterpart_name_col, "").strip()[:200] or None
            )

        counterpart_iban = None
        if column_map.counterpart_iban_col:
            counterpart_iban = (
                row.get(column_map.counterpart_iban_col, "").strip()[:34] or None
            )

        source_ref = f"{tx_date.isoformat()}:{amount_cents}:{i:04d}"

        result.append(
            RawTransaction(
                transaction_date=tx_date,
                value_date=None,
                amount_cents=amount_cents,
                purpose=purpose,
                counterpart_name=counterpart_name,
                counterpart_iban=counterpart_iban,
                source_ref=source_ref,
            )
        )
    return result


async def import_transactions(
    session: AsyncSession,
    bank_account_id: uuid.UUID,
    mandant_id: uuid.UUID,
    transactions: list[RawTransaction],
    source_format: str,
) -> tuple[int, int]:
    """Persist raw transactions, skip duplicates by source_ref.

    Returns (imported_count, skipped_count).
    Uses SELECT-first + INSERT pattern for MariaDB/PostgreSQL compatibility.
    """
    imported = 0
    skipped = 0

    for tx in transactions:
        if tx.source_ref:
            existing = (
                await session.execute(
                    select(BankTransaction).where(
                        BankTransaction.bank_account_id == bank_account_id,
                        BankTransaction.source_ref == tx.source_ref,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                skipped += 1
                continue

        bt = BankTransaction(
            mandant_id=mandant_id,
            bank_account_id=bank_account_id,
            transaction_date=tx.transaction_date,
            value_date=tx.value_date,
            amount_cents=tx.amount_cents,
            purpose=tx.purpose,
            counterpart_name=tx.counterpart_name,
            counterpart_iban=tx.counterpart_iban,
            source_format=source_format,
            source_ref=tx.source_ref,
        )
        session.add(bt)
        imported += 1

    await session.flush()
    return imported, skipped
