"""Aggregated dashboard diagnostics for operator workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dataset_validation_result import DatasetValidationResult
from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing
from app.models.ranking_run import RankingRun
from app.schemas.ranking import DiagnosticsSummaryResponse


def get_diagnostics_summary(db: Session) -> DiagnosticsSummaryResponse:
    total_ranking_runs = int(db.scalar(select(func.count()).select_from(RankingRun)) or 0)
    total_listings = int(db.scalar(select(func.count()).select_from(Listing)) or 0)

    status_rows = db.execute(
        select(IngestionJob.status, func.count(IngestionJob.id)).group_by(IngestionJob.status)
    ).all()
    ingestion_jobs_by_status = {str(status): int(count) for status, count in status_rows}

    latest = db.scalars(
        select(DatasetValidationResult).order_by(DatasetValidationResult.created_at.desc()).limit(8)
    ).all()
    latest_dataset_validations: list[dict[str, Any]] = []
    for row in latest:
        latest_dataset_validations.append(
            {
                "job_id": row.job_id,
                "status": row.status,
                "valid_rate": row.valid_rate,
                "invalid_rate": row.invalid_rate,
                "duplicate_rate": row.duplicate_rate,
                "price_null_rate": row.price_null_rate,
                "summary": row.summary,
                "created_at": (
                    row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None
                ),
            }
        )

    return DiagnosticsSummaryResponse(
        api_status="ok",
        total_ranking_runs=total_ranking_runs,
        total_listings=total_listings,
        ingestion_jobs_by_status=ingestion_jobs_by_status,
        latest_dataset_validations=latest_dataset_validations,
    )
