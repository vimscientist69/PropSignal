"""Week 4 run history, export, and diagnostics routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.api.week3_errors import error_json_response
from app.db.session import SessionLocal
from app.schemas.ranking import DiagnosticsSummaryResponse, RunDetailResponse, RunsListResponse
from app.services.dashboard_diagnostics import get_diagnostics_summary
from app.services.ranking_query import RankingRunNotFound
from app.services.ranking_runs import export_run_media, get_run_detail, list_run_summaries

router = APIRouter()


@router.get(
    "/runs",
    response_model=RunsListResponse,
    tags=["runs"],
)
def get_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> RunsListResponse:
    with SessionLocal() as db:
        return list_run_summaries(db, page=page, page_size=page_size)


@router.get(
    "/runs/{run_id}",
    response_model=RunDetailResponse,
    responses={404: {"description": "Run not found"}},
    tags=["runs"],
)
def get_run_by_id(request: Request, run_id: str) -> RunDetailResponse | Response:
    with SessionLocal() as db:
        try:
            return get_run_detail(db, run_id)
        except RankingRunNotFound as exc:
            return error_json_response(
                status_code=404,
                request=request,
                code="not_found",
                message=str(exc),
            )


@router.get(
    "/runs/{run_id}/export",
    responses={404: {"description": "Run not found"}},
    tags=["runs"],
)
def get_run_export(
    request: Request,
    run_id: str,
    export_format: Literal["csv", "json"] = Query(default="json", alias="format"),
    listing_detail: bool = Query(
        default=False,
        description=(
            "Include per-row listing detail (same payload as GET "
            "/rankings/{run_id}/listings/{listing_id})"
        ),
    ),
) -> Response:
    with SessionLocal() as db:
        try:
            body, media_type, filename = export_run_media(
                db,
                run_id,
                format_=export_format,
                include_listing_detail=listing_detail,
            )
        except RankingRunNotFound as exc:
            return error_json_response(
                status_code=404,
                request=request,
                code="not_found",
                message=str(exc),
            )
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=body, media_type=media_type, headers=headers)


@router.get(
    "/diagnostics/summary",
    response_model=DiagnosticsSummaryResponse,
    tags=["diagnostics"],
)
def get_diagnostics_summary_route() -> DiagnosticsSummaryResponse:
    with SessionLocal() as db:
        return get_diagnostics_summary(db)
