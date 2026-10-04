"""Require a website for registered companies.

Revision ID: 20261002_02
Revises: 20261001_01
Create Date: 2026-10-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261002_02"
down_revision: str | Sequence[str] | None = "20261001_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "companies",
        "website",
        existing_type=sa.String(length=500),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "companies",
        "website",
        existing_type=sa.String(length=500),
        nullable=True,
    )
