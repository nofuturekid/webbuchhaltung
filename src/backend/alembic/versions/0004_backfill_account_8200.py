"""backfill SKR03 account 8200 for existing mandants

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-10

Data migration only — no schema changes.
Inserts account 8200 ("Steuerfreie Erlöse (Inland)") for every SKR03 mandant
that does not already have it. Required by invoice_booking.py for 0%-VAT invoices.
"""

import uuid

from alembic import op  # type: ignore[attr-defined]
from sqlalchemy import text

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_ACCOUNT_NUMBER = "8200"
_ACCOUNT_NAME = "Steuerfreie Erlöse (Inland)"
_ACCOUNT_CLASS = "8xxx"
_TAX_TYPE = "steuerfrei"
_SKR_VARIANT = "skr03"


def upgrade() -> None:
    conn = op.get_bind()

    # Fetch all SKR03 mandant IDs that are missing account 8200.
    missing = conn.execute(
        text(
            """
            SELECT id
            FROM mandants
            WHERE id NOT IN (
                SELECT mandant_id
                FROM chart_of_accounts
                WHERE account_number = :account_number
                  AND skr_variant    = :skr_variant
            )
            AND id IN (
                SELECT DISTINCT mandant_id
                FROM chart_of_accounts
                WHERE skr_variant = :skr_variant
            )
            """
        ),
        {"account_number": _ACCOUNT_NUMBER, "skr_variant": _SKR_VARIANT},
    ).fetchall()

    for row in missing:
        mandant_id = row[0]
        conn.execute(
            text(
                """
                INSERT INTO chart_of_accounts
                    (id, mandant_id, account_number, name, account_class,
                     tax_type, skr_variant, is_custom, private_share_percent, is_active)
                VALUES
                    (:id, :mandant_id, :account_number, :name, :account_class,
                     :tax_type, :skr_variant, FALSE, 0, TRUE)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "mandant_id": str(mandant_id),
                "account_number": _ACCOUNT_NUMBER,
                "name": _ACCOUNT_NAME,
                "account_class": _ACCOUNT_CLASS,
                "tax_type": _TAX_TYPE,
                "skr_variant": _SKR_VARIANT,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Only delete rows that were inserted by this migration:
    # account 8200, skr03, not custom, and not referenced by any booking.
    conn.execute(
        text(
            """
            DELETE FROM chart_of_accounts
            WHERE account_number = :account_number
              AND skr_variant    = :skr_variant
              AND is_custom      = FALSE
              AND id NOT IN (
                  SELECT coa_id         FROM bookings WHERE coa_id         IS NOT NULL
                  UNION ALL
                  SELECT counter_coa_id FROM bookings WHERE counter_coa_id IS NOT NULL
              )
            """
        ),
        {"account_number": _ACCOUNT_NUMBER, "skr_variant": _SKR_VARIANT},
    )
