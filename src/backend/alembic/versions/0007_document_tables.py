"""add document capture table

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-10

Tables:
  - documents: uploaded document records per mandant, with optional
    link to an extracted JSON payload and an associated booking once
    the document has been processed and posted.
"""

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mandant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("mandants.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("extracted_json", sa.JSON(), nullable=True),
        sa.Column(
            "booking_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("bookings.id"),
            nullable=True,
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
    )


def downgrade() -> None:
    op.drop_table("documents")
