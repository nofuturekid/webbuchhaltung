"""add email_salutation and email_closing to mandants

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-10

Adds two nullable String columns to the mandants table for configurable
email salutation and closing lines. Existing rows receive NULL, which
triggers the hardcoded fallback in invoice_email.send_invoice_email().
"""

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mandants", sa.Column("email_salutation", sa.String(500), nullable=True)
    )
    op.add_column("mandants", sa.Column("email_closing", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("mandants", "email_closing")
    op.drop_column("mandants", "email_salutation")
