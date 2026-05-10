"""add invoice tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-09
"""

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend mandants with banking and SMTP fields
    op.add_column("mandants", sa.Column("iban", sa.String(34), nullable=True))
    op.add_column("mandants", sa.Column("bic", sa.String(11), nullable=True))
    op.add_column("mandants", sa.Column("smtp_host", sa.String(253), nullable=True))
    op.add_column(
        "mandants",
        sa.Column("smtp_port", sa.SmallInteger(), nullable=False, server_default="587"),
    )
    op.add_column("mandants", sa.Column("smtp_user", sa.String(254), nullable=True))
    op.add_column("mandants", sa.Column("smtp_password", sa.String(500), nullable=True))
    op.add_column("mandants", sa.Column("smtp_from", sa.String(254), nullable=True))
    op.add_column(
        "mandants", sa.Column("smtp_from_name", sa.String(200), nullable=True)
    )

    # customers
    op.create_table(
        "customers",
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
        sa.Column("country", sa.String(2), nullable=False, server_default="DE"),
        sa.Column("vat_id", sa.String(30), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
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

    # invoice_sequences
    op.create_table(
        "invoice_sequences",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            nullable=False,
        ),
        sa.Column("prefix", sa.String(20), nullable=False, server_default="RE"),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("year_reset", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_reset_year", sa.Integer(), nullable=True),
        sa.UniqueConstraint("mandant_id", name="uq_invoice_sequence_mandant"),
    )

    # invoices — created WITHOUT booking_id FK (added later to avoid circular dependency)
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column("invoice_number", sa.String(50), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.Enum("draft", "issued", "cancelled", name="invoice_status_enum"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("net_total_cents", sa.BigInteger(), nullable=True),
        sa.Column("vat_total_cents", sa.BigInteger(), nullable=True),
        sa.Column("gross_total_cents", sa.BigInteger(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "booking_id", sa.Uuid(as_uuid=True), nullable=True
        ),  # FK added after bookings extended
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

    # invoice_line_items
    op.create_table(
        "invoice_line_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("invoices.id"),
            nullable=False,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("unit_price_cents", sa.BigInteger(), nullable=False),
        sa.Column("vat_rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("net_total_cents", sa.BigInteger(), nullable=True),
        sa.Column("vat_amount_cents", sa.BigInteger(), nullable=True),
    )

    # invoice_templates
    op.create_table(
        "invoice_templates",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            nullable=False,
        ),
        sa.Column("logo_path", sa.String(500), nullable=True),
        sa.Column(
            "primary_color", sa.String(7), nullable=False, server_default="#000000"
        ),
        sa.Column(
            "font_family",
            sa.String(100),
            nullable=False,
            server_default="Arial, sans-serif",
        ),
        sa.Column("header_text", sa.Text(), nullable=True),
        sa.Column("footer_text", sa.Text(), nullable=True),
        sa.Column(
            "payment_terms_text",
            sa.String(200),
            nullable=False,
            server_default="Zahlbar innerhalb von 14 Tagen",
        ),
        sa.Column("custom_html_template", sa.Text(), nullable=True),
        sa.Column(
            "use_custom_template", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("mandant_id", name="uq_invoice_template_mandant"),
    )

    # Extend bookings with invoice_id (column only, FK added after invoices table exists)
    op.add_column(
        "bookings", sa.Column("invoice_id", sa.Uuid(as_uuid=True), nullable=True)
    )
    # Add FK for bookings.invoice_id → invoices
    op.create_foreign_key(
        "fk_bookings_invoice_id", "bookings", "invoices", ["invoice_id"], ["id"]
    )
    # Add FK for invoices.booking_id → bookings (circular, resolved by adding after both exist)
    op.create_foreign_key(
        "fk_invoices_booking_id", "invoices", "bookings", ["booking_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_invoices_booking_id", "invoices", type_="foreignkey")
    op.drop_constraint("fk_bookings_invoice_id", "bookings", type_="foreignkey")
    op.drop_column("bookings", "invoice_id")
    op.drop_table("invoice_templates")
    op.drop_table("invoice_line_items")
    op.drop_table("invoices")
    op.drop_table("invoice_sequences")
    op.drop_table("customers")
    for col in [
        "smtp_from_name",
        "smtp_from",
        "smtp_password",
        "smtp_user",
        "smtp_port",
        "smtp_host",
        "bic",
        "iban",
    ]:
        op.drop_column("mandants", col)
    op.execute("DROP TYPE IF EXISTS invoice_status_enum")
