"""Week 3 ranking and scoring profile API routes (thin handlers).

All strategy, profile resolution, and scoring math live in ``app.services.ranking_query``,
``ranking_signals``, and ``scoring`` — not in this module. Handlers only validate transport,
invoke services, and map errors to the §4.4 envelope.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.week3_errors import error_json_response
from app.db.session import SessionLocal
from app.models.dataset_validation_result import DatasetValidationResult
from app.models.ingestion_job import IngestionJob
from app.schemas.ranking import (
    DatasetSourceSummaryResponse,
    ErrorField,
    ListingDetailResponse,
    ProfileDetailResponse,
    ProfileSummaryResponse,
    RankingQueryRequest,
    RankingQueryResponse,
    StrategyPreset,
)
from app.services.ranking_query import (
    RankingListingNotInRun,
    RankingListingRowMissing,
    RankingRunNotFound,
    get_listing_detail,
    list_profiles,
    resolve_profile,
    run_ranking_query,
)

router = APIRouter()


@router.post(
    "/rankings/query",
    response_model=RankingQueryResponse,
    responses={400: {"description": "Invalid strategy or overrides"}},
    tags=["rankings"],
)
def post_rankings_query(
    request: Request, body: RankingQueryRequest
) -> RankingQueryResponse | JSONResponse:
    try:
        with SessionLocal() as db:
            return run_ranking_query(body, db=db)
    except ValueError as exc:
        message = str(exc)
        if "Unknown dataset source" in message:
            code = "unknown_dataset_source"
            field = "dataset_sources"
        elif "No listings found for the selected dataset sources" in message:
            code = "empty_dataset"
            field = "dataset_sources"
        else:
            code = "invalid_strategy"
            field = "strategy"
        return error_json_response(
            status_code=400,
            request=request,
            code=code,
            message=message,
            field_errors=[ErrorField(field=field, reason=message)],
        )


@router.get(
    "/rankings/{run_id}/listings/{listing_id}",
    response_model=ListingDetailResponse,
    responses={404: {"description": "Run not found"}},
    tags=["rankings"],
)
def get_ranking_listing_detail(
    request: Request,
    run_id: str,
    listing_id: int,
) -> ListingDetailResponse | JSONResponse:
    with SessionLocal() as db:
        try:
            return get_listing_detail(run_id, listing_id, db)
        except RankingRunNotFound as exc:
            return error_json_response(
                status_code=404,
                request=request,
                code="not_found",
                message=str(exc),
            )
        except (RankingListingNotInRun, RankingListingRowMissing) as exc:
            return error_json_response(
                status_code=404,
                request=request,
                code="not_found",
                message=str(exc),
            )


@router.get(
    "/scoring/profiles",
    response_model=list[ProfileSummaryResponse],
    tags=["scoring"],
)
def get_scoring_profiles() -> list[ProfileSummaryResponse]:
    return list_profiles()


@router.get(
    "/scoring/profiles/{preset}",
    response_model=ProfileDetailResponse,
    responses={400: {"description": "Profile resolution failed"}},
    tags=["scoring"],
)
def get_scoring_profile_preset(
    request: Request, preset: StrategyPreset
) -> ProfileDetailResponse | JSONResponse:
    try:
        return resolve_profile(preset)
    except ValueError as exc:
        return error_json_response(
            status_code=400,
            request=request,
            code="invalid_profile",
            message=str(exc),
            field_errors=[ErrorField(field="preset", reason=str(exc))],
        )


@router.get(
    "/datasets/sources",
    response_model=list[DatasetSourceSummaryResponse],
    tags=["rankings"],
)
def list_dataset_sources() -> list[DatasetSourceSummaryResponse]:
    with SessionLocal() as db:
        jobs = db.scalars(select(IngestionJob).order_by(IngestionJob.id.desc())).all()
        validation_by_job_id = {
            row.job_id: row for row in db.scalars(select(DatasetValidationResult)).all()
        }
    return [
        DatasetSourceSummaryResponse(
            source=f"job:{job.id}",
            job_id=job.id,
            input_path=job.input_path,
            status=job.status,
            records_total=job.records_total,
            records_valid=job.records_valid,
            records_invalid=job.records_invalid,
            started_at=job.started_at.isoformat() if job.started_at else None,
            finished_at=job.finished_at.isoformat() if job.finished_at else None,
            validation_status=(
                validation_by_job_id[job.id].status if job.id in validation_by_job_id else None
            ),
            validation_summary=(
                validation_by_job_id[job.id].summary if job.id in validation_by_job_id else None
            ),
        )
        for job in jobs
    ]
