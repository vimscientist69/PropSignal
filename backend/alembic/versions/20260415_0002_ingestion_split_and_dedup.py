"""ingestion split storage and dedup

Revision ID: 20260415_0002
Revises: 20260414_0001
Create Date: 2026-04-15 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260415_0002"
down_revision: str | None = "20260414_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ingestion_jobs",
        sa.Column("records_invalid", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("ingestion_jobs", sa.Column("error_summary", sa.Text(), nullable=True))
    op.add_column(
        "ingestion_jobs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column(
        "ingestion_jobs",
        "status",
        existing_type=sa.String(length=32),
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

    op.add_column("listings", sa.Column("source_hash", sa.String(length=64), nullable=True))
    op.add_column("listings", sa.Column("normalized_payload", sa.JSON(), nullable=True))
    op.execute(
        "UPDATE listings SET source_hash = md5(random()::text), normalized_payload = raw_payload"
    )
    op.alter_column("listings", "source_hash", nullable=False)
    op.alter_column("listings", "normalized_payload", nullable=False)
    op.drop_column("listings", "raw_payload")
    op.create_unique_constraint("uq_listings_source_hash", "listings", ["source_hash"])
    op.create_index(
        "uq_listings_source_site_listing_id_not_null",
        "listings",
        ["source_site", "listing_id"],
        unique=True,
        postgresql_where=sa.text("listing_id IS NOT NULL AND source_site IS NOT NULL"),
    )

    op.create_table(
        "raw_listings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("ingestion_jobs.id"), nullable=False),
        sa.Column("record_index", sa.Integer(), nullable=False),
        sa.Column("source_site", sa.String(length=128), nullable=True),
        sa.Column("listing_id", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_raw_listings_job_id"), "raw_listings", ["job_id"], unique=False)
    op.create_index(
        op.f("ix_raw_listings_record_index"),
        "raw_listings",
        ["record_index"],
        unique=False,
    )

    op.create_table(
        "rejected_listings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("ingestion_jobs.id"), nullable=False),
        sa.Column("record_index", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_rejected_listings_job_id"),
        "rejected_listings",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rejected_listings_record_index"),
        "rejected_listings",
        ["record_index"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rejected_listings_record_index"), table_name="rejected_listings")
    op.drop_index(op.f("ix_rejected_listings_job_id"), table_name="rejected_listings")
    op.drop_table("rejected_listings")

    op.drop_index(op.f("ix_raw_listings_record_index"), table_name="raw_listings")
    op.drop_index(op.f("ix_raw_listings_job_id"), table_name="raw_listings")
    op.drop_table("raw_listings")

    op.drop_index("uq_listings_source_site_listing_id_not_null", table_name="listings")
    op.drop_constraint("uq_listings_source_hash", "listings", type_="unique")
    op.add_column("listings", sa.Column("raw_payload", sa.JSON(), nullable=True))
    op.execute("UPDATE listings SET raw_payload = normalized_payload")
    op.alter_column("listings", "raw_payload", nullable=False)
    op.drop_column("listings", "normalized_payload")
    op.drop_column("listings", "source_hash")

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
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.drop_column("ingestion_jobs", "finished_at")
    op.drop_column("ingestion_jobs", "started_at")
    op.drop_column("ingestion_jobs", "error_summary")
    op.drop_column("ingestion_jobs", "records_invalid")
