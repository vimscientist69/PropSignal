"""add ranking run and profile backup tables

Revision ID: 20260430_0006
Revises: 20260424_0005
Create Date: 2026-04-30 18:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260430_0006"
down_revision: str | None = "20260424_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scoring_profile_backups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.String(length=128), nullable=False),
        sa.Column("profile_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("profile_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_fingerprint"),
    )
    op.create_index(
        op.f("ix_scoring_profile_backups_profile_fingerprint"),
        "scoring_profile_backups",
        ["profile_fingerprint"],
        unique=True,
    )
    op.create_index(
        op.f("ix_scoring_profile_backups_profile_id"),
        "scoring_profile_backups",
        ["profile_id"],
        unique=False,
    )

    op.create_table(
        "ranking_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("query_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("strategy_preset", sa.String(length=64), nullable=False),
        sa.Column("resolved_profile_id", sa.String(length=128), nullable=False),
        sa.Column("profile_row_id", sa.Integer(), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("result_window", sa.JSON(), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["profile_row_id"], ["scoring_profile_backups.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        op.f("ix_ranking_runs_profile_row_id"),
        "ranking_runs",
        ["profile_row_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ranking_runs_query_fingerprint"),
        "ranking_runs",
        ["query_fingerprint"],
        unique=False,
    )
    op.create_index(op.f("ix_ranking_runs_run_id"), "ranking_runs", ["run_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_ranking_runs_run_id"), table_name="ranking_runs")
    op.drop_index(op.f("ix_ranking_runs_query_fingerprint"), table_name="ranking_runs")
    op.drop_index(op.f("ix_ranking_runs_profile_row_id"), table_name="ranking_runs")
    op.drop_table("ranking_runs")

    op.drop_index(
        op.f("ix_scoring_profile_backups_profile_id"),
        table_name="scoring_profile_backups",
    )
    op.drop_index(
        op.f("ix_scoring_profile_backups_profile_fingerprint"),
        table_name="scoring_profile_backups",
    )
    op.drop_table("scoring_profile_backups")
