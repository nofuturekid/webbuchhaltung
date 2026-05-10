"""add bank accounts and bank transactions tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-10

Tables:
  - bank_accounts: master record for a bank account per mandant,
    identified by IBAN, linked to the mandant that owns it.
  - bank_transactions: individual bank statement lines imported from
    MT940 or CSV files, with optional link to a posted booking once
    the transaction has been matched and reconciled.

Deferred FK:
  Activates the foreign key from bookings.bank_account_id → bank_accounts.id
  that was left as a bare column in Phase 2 (comment: "FK → bank_accounts (Phase 2)").
"""

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # bank_accounts — one row per bank account per mandant
    # -----------------------------------------------------------------------
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("iban", sa.String(34), nullable=False),
        sa.Column("bic", sa.String(11), nullable=True),
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default="EUR",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "mandant_id",
            "iban",
            name="uq_bank_account_mandant_iban",
        ),
    )

    # -----------------------------------------------------------------------
    # bank_transactions — one row per statement line imported from MT940/CSV
    # -----------------------------------------------------------------------
    op.create_table(
        "bank_transactions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            nullable=False,
        ),
        sa.Column(
            "bank_account_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("bank_accounts.id"),
            nullable=False,
        ),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default="EUR",
        ),
        sa.Column("purpose", sa.String(500), nullable=True),
        sa.Column("counterpart_name", sa.String(200), nullable=True),
        sa.Column("counterpart_iban", sa.String(34), nullable=True),
        # "mt940" or "csv" — String avoids ALTER TYPE issues on MariaDB
        sa.Column("source_format", sa.String(10), nullable=False),
        # Deduplication key scoped to the bank account; NULL means no dedup key
        sa.Column("source_ref", sa.String(100), nullable=True),
        # "unmatched", "matched", "posted", "ignored"
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="unmatched",
        ),
        sa.Column(
            "booking_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("bookings.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount_cents != 0",
            name="ck_bank_transaction_amount_nonzero",
        ),
        sa.UniqueConstraint(
            "bank_account_id",
            "source_ref",
            name="uq_bank_transaction_source_ref",
        ),
    )

    # -----------------------------------------------------------------------
    # Activate deferred FK: bookings.bank_account_id → bank_accounts.id
    # This column was added as a bare Uuid column in Phase 2 with the comment
    # "FK → bank_accounts (Phase 2)" — now that bank_accounts exists we wire it.
    # -----------------------------------------------------------------------
    op.create_foreign_key(
        "fk_bookings_bank_account_id",
        "bookings",
        "bank_accounts",
        ["bank_account_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop the deferred FK first so bank_accounts can be dropped
    op.drop_constraint(
        "fk_bookings_bank_account_id",
        "bookings",
        type_="foreignkey",
    )

    op.drop_table("bank_transactions")
    op.drop_table("bank_accounts")
