"""Week 3 ranking and scoring profile API routes (thin handlers)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.week3_errors import error_json_response
from app.db.session import SessionLocal
from app.models.ranking_run import RankingRun
from app.schemas.ranking import (
    ErrorField,
    ListingDetailResponse,
    ProfileDetailResponse,
    ProfileSummaryResponse,
    RankingQueryRequest,
    RankingQueryResponse,
    StrategyPreset,
)
from app.services.ranking_query import (
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
        return error_json_response(
            status_code=400,
            request=request,
            code="invalid_strategy",
            message=str(exc),
            field_errors=[ErrorField(field="strategy", reason=str(exc))],
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
        run = db.scalar(select(RankingRun).where(RankingRun.run_id == run_id))
    if run is None:
        return error_json_response(
            status_code=404,
            request=request,
            code="not_found",
            message=f"No ranking run found for run_id={run_id!r}.",
        )
    return get_listing_detail(run_id, listing_id)


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
