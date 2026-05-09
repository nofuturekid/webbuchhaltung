"""seed_data

Revision ID: 0002
Revises: a5138fdc66fa
Create Date: 2026-05-09
"""

import json
from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]

revision = "0002"
down_revision = "a5138fdc66fa"
branch_labels = None
depends_on = None

SEED_DIR = Path(__file__).parent.parent.parent / "seed"


def upgrade() -> None:
    conn = op.get_bind()
    tax_keys = json.loads((SEED_DIR / "tax_keys.json").read_text())
    for tk in tax_keys:
        if conn.dialect.name == "postgresql":
            stmt = sa.text(
                "INSERT INTO tax_keys (code, description, tax_rate, tax_type) "
                "VALUES (:code, :description, :tax_rate, :tax_type) "
                "ON CONFLICT (code) DO NOTHING"
            )
        else:
            stmt = sa.text(
                "INSERT IGNORE INTO tax_keys (code, description, tax_rate, tax_type) "
                "VALUES (:code, :description, :tax_rate, :tax_type)"
            )
        conn.execute(
            stmt,
            {
                "code": tk["code"],
                "description": tk["description"],
                "tax_rate": Decimal(tk["tax_rate"]) if tk["tax_rate"] else None,
                "tax_type": tk["tax_type"],
            },
        )


_SEEDED_CODES = [0, 2, 3, 9, 10, 40, 41, 44, 48]


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(
            sa.text("DELETE FROM tax_keys WHERE code = ANY(:codes)"),
            {"codes": _SEEDED_CODES},
        )
    else:
        for code in _SEEDED_CODES:
            conn.execute(
                sa.text("DELETE FROM tax_keys WHERE code = :code"),
                {"code": code},
            )
