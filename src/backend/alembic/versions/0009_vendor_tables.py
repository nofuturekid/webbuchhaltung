"""add vendor and vendor invoice tables + AP account backfill

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-10

Section A — Tables:
  - vendors: master record for a supplier/vendor per mandant, with contact
    and SEPA payment data (IBAN/BIC) used for outgoing SEPA payment XML.
  - vendor_invoices: incoming supplier invoices (Eingangsrechnungen) per
    mandant, optionally linked to a posted booking and/or an uploaded
    document from the LLM capture pipeline.

Section B — Data:
  Backfills SKR03 and SKR04 chart_of_accounts entries required for
  accounts-payable (AP) bookings.
  Uses the same safe INSERT pattern as migration 0006: fetch affected
  mandants, skip if the account already exists for that mandant.
"""

import uuid

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]
from sqlalchemy import text

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# SKR account data — used in upgrade()
# Each tuple: (account_number, name, account_class, tax_type)
# ---------------------------------------------------------------------------

_SKR03_ACCOUNTS = [
    # Verbindlichkeiten aus Lieferungen und Leistungen (AP trade payables)
    ("1600", "Verbindlichkeiten aus Lieferungen und Leistungen", "1xxx", None),
    # Vorsteuer (input VAT) accounts needed when booking vendor invoices
    ("1576", "Vorsteuer 7%", "1xxx", "VSt"),
    ("1571", "Vorsteuer 19%", "1xxx", "VSt"),
]

_SKR04_ACCOUNTS = [
    # Verbindlichkeiten aus Lieferungen und Leistungen (AP trade payables)
    ("3300", "Verbindlichkeiten aus Lieferungen und Leistungen", "3xxx", None),
    # Vorsteuer (input VAT) accounts needed when booking vendor invoices
    ("1406", "Vorsteuer 19%", "1xxx", "VSt"),
    ("1401", "Vorsteuer 7%", "1xxx", "VSt"),
]


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Section A — New tables
    # -----------------------------------------------------------------------

    # vendors — supplier master record per mandant
    op.create_table(
        "vendors",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("street", sa.String(200), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column(
            "country",
            sa.String(2),
            nullable=False,
            server_default="DE",
        ),
        sa.Column("vat_id", sa.String(30), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        # SEPA payment fields — used when generating outgoing payment XML
        sa.Column("bank_iban", sa.String(34), nullable=True),
        sa.Column("bank_bic", sa.String(11), nullable=True),
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
    )

    # vendor_invoices — incoming supplier invoice (Eingangsrechnung) per mandant
    op.create_table(
        "vendor_invoices",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            nullable=False,
        ),
        sa.Column(
            "vendor_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("vendors.id"),
            nullable=False,
        ),
        # vendor's own reference number printed on the supplier invoice
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column(
            "vat_amount_cents",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default="EUR",
        ),
        # "draft", "posted", "paid", "cancelled"
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
        # linked posting once the invoice has been booked
        sa.Column(
            "booking_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("bookings.id"),
            nullable=True,
        ),
        # linked document from LLM capture pipeline
        sa.Column(
            "document_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
            "amount_cents > 0",
            name="ck_vendor_invoice_amount_positive",
        ),
        sa.UniqueConstraint(
            "mandant_id",
            "vendor_id",
            "invoice_number",
            name="uq_vendor_invoice_number",
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
        for account_number, name, account_class, tax_type in _SKR03_ACCOUNTS:
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
                             :account_class, :tax_type, 'skr03', FALSE, 0, TRUE)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "mandant_id": mandant_id,
                        "account_number": account_number,
                        "name": name,
                        "account_class": account_class,
                        "tax_type": tax_type,
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
        for account_number, name, account_class, tax_type in _SKR04_ACCOUNTS:
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
                             :account_class, :tax_type, 'skr04', FALSE, 0, TRUE)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "mandant_id": mandant_id,
                        "account_number": account_number,
                        "name": name,
                        "account_class": account_class,
                        "tax_type": tax_type,
                    },
                )


def downgrade() -> None:
    # Drop vendor_invoices first (it references vendors)
    op.drop_table("vendor_invoices")
    op.drop_table("vendors")
    # Note: SKR account backfill is NOT reversed in downgrade.
    # Data-only inserts are not safely reversible — accounts may have been
    # used in bookings by the time a downgrade is needed.
