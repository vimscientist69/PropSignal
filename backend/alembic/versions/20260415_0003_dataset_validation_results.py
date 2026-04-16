"""add dataset validation results table

Revision ID: 20260415_0003
Revises: 20260415_0002
Create Date: 2026-04-15 00:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260415_0003"
down_revision: str | None = "20260415_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dataset_validation_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("ingestion_jobs.id"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("valid_rate", sa.Float(), nullable=False),
        sa.Column("invalid_rate", sa.Float(), nullable=False),
        sa.Column("duplicate_rate", sa.Float(), nullable=False),
        sa.Column("price_null_rate", sa.Float(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("report_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("job_id", name="uq_dataset_validation_results_job_id"),
    )
    op.create_index(
        op.f("ix_dataset_validation_results_job_id"),
        "dataset_validation_results",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_dataset_validation_results_job_id"),
        table_name="dataset_validation_results",
    )
    op.drop_table("dataset_validation_results")
