"""add records_considered to ranking_runs for run history API

Revision ID: 20260511_0009
Revises: 20260507_0008
Create Date: 2026-05-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260511_0009"
down_revision: str | None = "20260507_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ranking_runs",
        sa.Column("records_considered", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("ranking_runs", "records_considered", server_default=None)


def downgrade() -> None:
    op.drop_column("ranking_runs", "records_considered")
