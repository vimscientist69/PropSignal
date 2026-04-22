"""add score result explanation payload

Revision ID: 20260415_0004
Revises: 20260415_0003
Create Date: 2026-04-15 01:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260415_0004"
down_revision: str | None = "20260415_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("score_results", sa.Column("explanation", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("score_results", "explanation")
