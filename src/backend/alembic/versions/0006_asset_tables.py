"""add asset management tables and SKR backfill

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-10

Section A — Tables:
  - assets: fixed-asset master records per mandant
  - asset_sequences: per-mandant counter for asset numbers (mirrors BookingSequence)
  - depreciation_schedules: pre-computed depreciation plan rows, optionally linked
    to a posted booking once the period is closed

Section B — Data:
  Backfills SKR03 and SKR04 chart_of_accounts entries required for
  asset purchase, depreciation, and disposal bookings.
  Uses the same safe INSERT pattern as migration 0004: fetch affected mandants,
  skip if the account already exists for that mandant.
"""

import uuid

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]
from sqlalchemy import text

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# SKR account data — used in both upgrade() and downgrade()
# Each tuple: (account_number, name, account_class)
# ---------------------------------------------------------------------------

_SKR03_ACCOUNTS = [
    ("0160", "Geschäftsausstattung", "0xxx"),
    ("0180", "Geringwertige Wirtschaftsgüter", "0xxx"),
    ("4570", "Abschreibungen auf Kraftfahrzeuge", "4xxx"),
    ("4800", "Abschreibungen auf Sachanlagen", "4xxx"),
    ("2680", "Erträge aus Anlagenabgang", "2xxx"),
    ("4855", "Verluste aus Anlagenabgang", "4xxx"),
]

_SKR04_ACCOUNTS = [
    ("0160", "Büroausstattung", "0xxx"),
    ("6220", "Abschreibungen auf Sachanlagen", "6xxx"),
    ("2310", "Erträge aus Anlagenabgang", "2xxx"),
    ("4830", "Verluste aus Anlagenabgang", "4xxx"),
]


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Section A — New tables
    # -----------------------------------------------------------------------

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            nullable=False,
        ),
        sa.Column("asset_number", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("purchase_amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("useful_life_months", sa.Integer(), nullable=False),
        sa.Column(
            "depreciation_method",
            sa.String(10),
            nullable=False,
            server_default="linear",
        ),
        sa.Column(
            "residual_value_cents",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("disposal_date", sa.Date(), nullable=True),
        sa.Column("disposal_amount_cents", sa.BigInteger(), nullable=True),
        sa.Column(
            "coa_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("chart_of_accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "depreciation_coa_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("chart_of_accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(10),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
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
        sa.CheckConstraint(
            "purchase_amount_cents > 0",
            name="ck_asset_purchase_amount_positive",
        ),
        sa.CheckConstraint(
            "useful_life_months > 0",
            name="ck_asset_useful_life_positive",
        ),
        sa.UniqueConstraint(
            "mandant_id",
            "asset_number",
            name="uq_asset_mandant_number",
        ),
    )

    op.create_table(
        "asset_sequences",
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            primary_key=True,
        ),
        sa.Column(
            "next_value",
            sa.BigInteger(),
            nullable=False,
            server_default="1",
        ),
    )

    op.create_table(
        "depreciation_schedules",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "asset_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            nullable=False,
        ),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("cumulative_depreciation_cents", sa.BigInteger(), nullable=False),
        sa.Column("net_book_value_cents", sa.BigInteger(), nullable=False),
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
        sa.UniqueConstraint(
            "asset_id",
            "period_year",
            "period_month",
            name="uq_depreciation_schedule_period",
        ),
    )

    # -----------------------------------------------------------------------
    # Section B — SKR account backfill
    # -----------------------------------------------------------------------

    conn = op.get_bind()

    skr03_mandants = conn.execute(
        text(
            """
            SELECT id
            FROM mandants
            WHERE id IN (
                SELECT DISTINCT mandant_id
                FROM chart_of_accounts
                WHERE skr_variant = 'skr03'
            )
            """
        )
    ).fetchall()

    for row in skr03_mandants:
        mandant_id = str(row[0])
        for account_number, name, account_class in _SKR03_ACCOUNTS:
            already_exists = conn.execute(
                text(
                    """
                    SELECT 1 FROM chart_of_accounts
                    WHERE mandant_id     = :mandant_id
                      AND account_number = :account_number
                    """
                ),
                {"mandant_id": mandant_id, "account_number": account_number},
            ).scalar()
            if not already_exists:
                conn.execute(
                    text(
                        """
                        INSERT INTO chart_of_accounts
                            (id, mandant_id, account_number, name, account_class,
                             tax_type, skr_variant, is_custom,
                             private_share_percent, is_active)
                        VALUES
                            (:id, :mandant_id, :account_number, :name,
                             :account_class, NULL, 'skr03', FALSE, 0, TRUE)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "mandant_id": mandant_id,
                        "account_number": account_number,
                        "name": name,
                        "account_class": account_class,
                    },
                )

    skr04_mandants = conn.execute(
        text(
            """
            SELECT id
            FROM mandants
            WHERE id IN (
                SELECT DISTINCT mandant_id
                FROM chart_of_accounts
                WHERE skr_variant = 'skr04'
            )
            """
        )
    ).fetchall()

    for row in skr04_mandants:
        mandant_id = str(row[0])
        for account_number, name, account_class in _SKR04_ACCOUNTS:
            already_exists = conn.execute(
                text(
                    """
                    SELECT 1 FROM chart_of_accounts
                    WHERE mandant_id     = :mandant_id
                      AND account_number = :account_number
                    """
                ),
                {"mandant_id": mandant_id, "account_number": account_number},
            ).scalar()
            if not already_exists:
                conn.execute(
                    text(
                        """
                        INSERT INTO chart_of_accounts
                            (id, mandant_id, account_number, name, account_class,
                             tax_type, skr_variant, is_custom,
                             private_share_percent, is_active)
                        VALUES
                            (:id, :mandant_id, :account_number, :name,
                             :account_class, NULL, 'skr04', FALSE, 0, TRUE)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "mandant_id": mandant_id,
                        "account_number": account_number,
                        "name": name,
                        "account_class": account_class,
                    },
                )


def downgrade() -> None:
    op.drop_table("depreciation_schedules")
    op.drop_table("asset_sequences")
    op.drop_table("assets")

    conn = op.get_bind()

    for account_number, _, _ in _SKR03_ACCOUNTS:
        conn.execute(
            text(
                """
                DELETE FROM chart_of_accounts
                WHERE account_number = :account_number
                  AND skr_variant    = 'skr03'
                  AND is_custom      = FALSE
                  AND id NOT IN (
                      SELECT coa_id         FROM bookings WHERE coa_id         IS NOT NULL
                      UNION ALL
                      SELECT counter_coa_id FROM bookings WHERE counter_coa_id IS NOT NULL
                  )
                """
            ),
            {"account_number": account_number},
        )

    for account_number, _, _ in _SKR04_ACCOUNTS:
        conn.execute(
            text(
                """
                DELETE FROM chart_of_accounts
                WHERE account_number = :account_number
                  AND skr_variant    = 'skr04'
                  AND is_custom      = FALSE
                  AND id NOT IN (
                      SELECT coa_id         FROM bookings WHERE coa_id         IS NOT NULL
                      UNION ALL
                      SELECT counter_coa_id FROM bookings WHERE counter_coa_id IS NOT NULL
                  )
                """
            ),
            {"account_number": account_number},
        )
