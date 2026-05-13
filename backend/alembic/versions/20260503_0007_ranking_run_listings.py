"""ranking run listing rows for detail reproducibility

Revision ID: 20260503_0007
Revises: 20260430_0006
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260503_0007"
down_revision: str | None = "20260430_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ranking_run_listings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ranking_run_id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("deal_reason", sa.Text(), nullable=False),
        sa.Column("explanation_snapshot", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"]),
        sa.ForeignKeyConstraint(["ranking_run_id"], ["ranking_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ranking_run_id", "listing_id", name="uq_ranking_run_listing"),
    )
    op.create_index(
        op.f("ix_ranking_run_listings_listing_id"),
        "ranking_run_listings",
        ["listing_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ranking_run_listings_ranking_run_id"),
        "ranking_run_listings",
        ["ranking_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ranking_run_listings_ranking_run_id"),
        table_name="ranking_run_listings",
    )
    op.drop_index(
        op.f("ix_ranking_run_listings_listing_id"),
        table_name="ranking_run_listings",
    )
    op.drop_table("ranking_run_listings")
