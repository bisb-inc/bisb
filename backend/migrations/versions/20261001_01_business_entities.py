"""Create MVP business entities.

Revision ID: 20261001_01
Revises:
Create Date: 2026-10-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261001_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("search_term", sa.String(length=240), nullable=True),
        sa.Column("market", sa.Text(), nullable=True),
        sa.Column("products", sa.Text(), nullable=True),
        sa.Column("audience", sa.Text(), nullable=True),
    )
    op.create_table(
        "analysis_companies",
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("analysis_id", "company_id"),
        sa.CheckConstraint("role IN ('TARGET', 'COMPETITOR')", name="ck_analysis_company_role"),
    )
    op.create_index(
        "uq_analysis_target",
        "analysis_companies",
        ["analysis_id"],
        unique=True,
        postgresql_where=sa.text("role = 'TARGET'"),
        sqlite_where=sa.text("role = 'TARGET'"),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("company_id", "source", "url", name="uq_event_company_source_url"),
        sa.CheckConstraint("source IN ('GNEWS', 'X')", name="ck_event_source"),
    )
    op.create_index("ix_event_timeline", "events", ["published_at", "collected_at"])


def downgrade() -> None:
    op.drop_index("ix_event_timeline", table_name="events")
    op.drop_table("events")
    op.drop_index("uq_analysis_target", table_name="analysis_companies")
    op.drop_table("analysis_companies")
    op.drop_table("companies")
    op.drop_table("analyses")
