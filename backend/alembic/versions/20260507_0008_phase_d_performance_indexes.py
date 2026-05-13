"""phase d performance indexes for ranking/filter paths

Revision ID: 20260507_0008
Revises: 20260503_0007
Create Date: 2026-05-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260507_0008"
down_revision: str | None = "20260503_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_listings_job_id_id",
        "listings",
        ["job_id", "id"],
        unique=False,
    )
    op.create_index(
        "ix_listings_core_filters",
        "listings",
        ["province", "city", "suburb", "property_type"],
        unique=False,
    )
    op.create_index(
        "ix_listings_job_id_price",
        "listings",
        ["job_id", "price"],
        unique=False,
    )
    op.create_index(
        "ix_score_results_job_id_created_at",
        "score_results",
        ["job_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_score_results_job_id_created_at", table_name="score_results")
    op.drop_index("ix_listings_job_id_price", table_name="listings")
    op.drop_index("ix_listings_core_filters", table_name="listings")
    op.drop_index("ix_listings_job_id_id", table_name="listings")
