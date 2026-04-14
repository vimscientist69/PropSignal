"""initial pre-week1 schema

Revision ID: 20260414_0001
Revises:
Create Date: 2026-04-14 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260414_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("input_path", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("records_total", sa.Integer(), nullable=False),
        sa.Column("records_valid", sa.Integer(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("location", sa.String(length=512), nullable=False),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column("bathrooms", sa.Float(), nullable=False),
        sa.Column("property_type", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("agent_name", sa.String(length=256), nullable=True),
        sa.Column("agent_phone", sa.String(length=64), nullable=True),
        sa.Column("agency_name", sa.String(length=256), nullable=True),
        sa.Column("listing_id", sa.String(length=128), nullable=True),
        sa.Column("date_posted", sa.Date(), nullable=True),
        sa.Column("erf_size", sa.Float(), nullable=True),
        sa.Column("floor_size", sa.Float(), nullable=True),
        sa.Column("rates_and_taxes", sa.Float(), nullable=True),
        sa.Column("levies", sa.Float(), nullable=True),
        sa.Column("garages", sa.Integer(), nullable=True),
        sa.Column("parking", sa.Integer(), nullable=True),
        sa.Column("en_suite", sa.Integer(), nullable=True),
        sa.Column("lounges", sa.Integer(), nullable=True),
        sa.Column("backup_power", sa.Boolean(), nullable=True),
        sa.Column("security", sa.Boolean(), nullable=True),
        sa.Column("pets_allowed", sa.Boolean(), nullable=True),
        sa.Column("listing_url", sa.String(length=1024), nullable=True),
        sa.Column("suburb", sa.String(length=256), nullable=True),
        sa.Column("city", sa.String(length=256), nullable=True),
        sa.Column("province", sa.String(length=256), nullable=True),
        sa.Column("is_auction", sa.Boolean(), nullable=True),
        sa.Column("is_private_seller", sa.Boolean(), nullable=True),
        sa.Column("source_site", sa.String(length=128), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["ingestion_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_listings_job_id"), "listings", ["job_id"], unique=False)
    op.create_index(op.f("ix_listings_listing_id"), "listings", ["listing_id"], unique=False)

    op.create_table(
        "score_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("deal_reason", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["ingestion_jobs.id"]),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_score_results_job_id"), "score_results", ["job_id"], unique=False)
    op.create_index(
        op.f("ix_score_results_listing_id"),
        "score_results",
        ["listing_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_score_results_listing_id"), table_name="score_results")
    op.drop_index(op.f("ix_score_results_job_id"), table_name="score_results")
    op.drop_table("score_results")

    op.drop_index(op.f("ix_listings_listing_id"), table_name="listings")
    op.drop_index(op.f("ix_listings_job_id"), table_name="listings")
    op.drop_table("listings")

    op.drop_table("ingestion_jobs")
