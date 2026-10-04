"""Add optional AI enrichment for collected events.

Revision ID: 20261003_03
Revises: 20261002_02
Create Date: 2026-10-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261003_03"
down_revision: str | Sequence[str] | None = "20261002_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_analyses",
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("competitive_impact", sa.String(length=8), nullable=False),
        sa.Column("sentiment", sa.String(length=8), nullable=False),
        sa.Column("relevance_score", sa.Integer(), nullable=False),
        sa.Column("justification", sa.String(length=500), nullable=False),
        sa.Column("provider", sa.String(length=8), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 100",
            name="ck_event_analysis_relevance_score",
        ),
        sa.CheckConstraint(
            "category IN ('PRODUCT', 'PRICING', 'PARTNERSHIP', 'EXPANSION', "
            "'FINANCIAL_RESULTS', 'REGULATORY', 'M_AND_A', 'PEOPLE', 'TECHNOLOGY', 'OTHER')",
            name="eventanalysiscategory",
        ),
        sa.CheckConstraint(
            "competitive_impact IN ('LOW', 'MEDIUM', 'HIGH')", name="competitiveimpact"
        ),
        sa.CheckConstraint(
            "sentiment IN ('NEGATIVE', 'NEUTRAL', 'POSITIVE')", name="eventsentiment"
        ),
        sa.CheckConstraint("provider IN ('GEMINI', 'MOCK')", name="analysisengine"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("event_analyses")
