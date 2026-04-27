"""add analyzed ingestion job status

Revision ID: 20260424_0005
Revises: 20260415_0004
Create Date: 2026-04-24 00:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260424_0005"
down_revision: str | None = "20260415_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "ingestion_jobs",
        "status",
        existing_type=sa.Enum(
            "created",
            "processing",
            "completed",
            "completed_with_errors",
            "failed",
            name="ingestion_job_status",
            native_enum=False,
        ),
        type_=sa.Enum(
            "created",
            "processing",
            "completed",
            "completed_with_errors",
            "analyzed",
            "failed",
            name="ingestion_job_status",
            native_enum=False,
        ),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute("UPDATE ingestion_jobs SET status = 'completed' WHERE status = 'analyzed'")
    op.alter_column(
        "ingestion_jobs",
        "status",
        existing_type=sa.Enum(
            "created",
            "processing",
            "completed",
            "completed_with_errors",
            "analyzed",
            "failed",
            name="ingestion_job_status",
            native_enum=False,
        ),
        type_=sa.Enum(
            "created",
            "processing",
            "completed",
            "completed_with_errors",
            "failed",
            name="ingestion_job_status",
            native_enum=False,
        ),
        existing_nullable=False,
    )
