"""Persisted ranking run listing, detail, and export (Week 4 dashboard APIs)."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.ranking_run import RankingRun
from app.models.ranking_run_listing import RankingRunListing
from app.schemas.ranking import (
    RankingResultItem,
    RunDetailResponse,
    RunsListResponse,
    RunSummaryItem,
)
from app.services.ranking_query import (
    RankingRunNotFound,
    build_ranking_result_item,
    get_listing_detail,
)


def _run_created_iso(run: RankingRun) -> str:
    created = run.created_at
    if getattr(created, "tzinfo", None) is None:
        created = created.replace(tzinfo=UTC)
    text = created.isoformat()
    return text.replace("+00:00", "Z")


def _source_count(request_payload: dict[str, Any]) -> int:
    sources = request_payload.get("dataset_sources")
    if isinstance(sources, list):
        return len(sources)
    return 0


def list_run_summaries(db: Session, *, page: int = 1, page_size: int = 20) -> RunsListResponse:
    total = int(db.scalar(select(func.count()).select_from(RankingRun)) or 0)
    offset = (page - 1) * page_size
    runs = db.scalars(
        select(RankingRun).order_by(RankingRun.created_at.desc()).offset(offset).limit(page_size)
    ).all()
    items: list[RunSummaryItem] = []
    for run in runs:
        items.append(
            RunSummaryItem(
                run_id=run.run_id,
                created_at=_run_created_iso(run),
                strategy_preset=run.strategy_preset,
                profile_id=run.resolved_profile_id,
                profile_row_id=run.profile_row_id,
                source_count=_source_count(run.request_payload),
                records_considered=run.records_considered,
                result_count=run.result_count,
                latency_ms=None,
            )
        )
    return RunsListResponse(items=items, page=page, page_size=page_size, total=total)


def get_run_detail(db: Session, run_id: str) -> RunDetailResponse:
    run = db.scalar(select(RankingRun).where(RankingRun.run_id == run_id))
    if run is None:
        raise RankingRunNotFound(f"No ranking run found for run_id={run_id!r}.")

    stmt = (
        select(RankingRunListing, Listing)
        .join(Listing, Listing.id == RankingRunListing.listing_id)
        .where(RankingRunListing.ranking_run_id == run.id)
        .order_by(RankingRunListing.ordinal)
    )
    pairs = db.execute(stmt).all()
    results: list[RankingResultItem] = []
    for rrl, listing in pairs:
        results.append(
            build_ranking_result_item(
                listing,
                score=rrl.score,
                confidence=rrl.confidence,
                deal_reason=rrl.deal_reason,
                run_id=run.run_id,
            )
        )

    return RunDetailResponse(
        run_id=run.run_id,
        created_at=_run_created_iso(run),
        query_fingerprint=run.query_fingerprint,
        strategy_preset=run.strategy_preset,
        profile_id=run.resolved_profile_id,
        profile_row_id=run.profile_row_id,
        source_count=_source_count(run.request_payload),
        records_considered=run.records_considered,
        result_count=run.result_count,
        request_snapshot=run.request_payload,
        result_window=run.result_window,
        results=results,
        latency_ms=None,
    )


def build_run_export_payload(
    db: Session, run_id: str, *, include_listing_detail: bool = False
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    detail = get_run_detail(db, run_id)
    metadata = {
        "run_id": detail.run_id,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "strategy_preset": detail.strategy_preset,
        "profile_id": detail.profile_id,
        "profile_row_id": detail.profile_row_id,
        "dataset_sources": detail.request_snapshot.get("dataset_sources", []),
        "filters": detail.request_snapshot.get("filters", {}),
        "strategy": detail.request_snapshot.get("strategy", {}),
        "result_window": detail.result_window,
        "listing_detail_included": include_listing_detail,
    }
    rows: list[dict[str, Any]] = []
    for item in detail.results:
        row = item.model_dump(mode="json")
        if include_listing_detail:
            listing_detail = get_listing_detail(run_id, item.listing_id, db)
            row["listing_detail"] = listing_detail.model_dump(mode="json")
        rows.append(row)
    return metadata, rows


def export_run_as_json_bytes(
    db: Session, run_id: str, *, include_listing_detail: bool = False
) -> bytes:
    metadata, rows = build_run_export_payload(
        db, run_id, include_listing_detail=include_listing_detail
    )
    payload = {"export_metadata": metadata, "results": rows}
    return json.dumps(payload, indent=2).encode("utf-8")


def export_run_as_csv_text(
    db: Session, run_id: str, *, include_listing_detail: bool = False
) -> str:
    metadata, rows = build_run_export_payload(
        db, run_id, include_listing_detail=include_listing_detail
    )
    buf = io.StringIO()
    meta_line = "# export_metadata: " + json.dumps(metadata, separators=(",", ":"))
    buf.write(meta_line + "\n")

    def _flatten(row: dict[str, Any]) -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for key, val in row.items():
            if isinstance(val, (dict, list)):
                flat[key] = json.dumps(val, separators=(",", ":"))
            elif val is None:
                flat[key] = ""
            else:
                flat[key] = val
        return flat

    flat_rows = [_flatten(r) for r in rows]
    if not flat_rows:
        buf.write("listing_id,score,confidence,deal_reason\n")
        return buf.getvalue()
    fieldnames = list(flat_rows[0].keys())
    for r in flat_rows[1:]:
        for key in r:
            if key not in fieldnames:
                fieldnames.append(key)
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(flat_rows)
    return buf.getvalue()


def export_run_media(
    db: Session,
    run_id: str,
    *,
    format_: Literal["json", "csv"],
    include_listing_detail: bool = False,
) -> tuple[bytes, str, str]:
    suffix = "-full-detail" if include_listing_detail else ""
    if format_ == "json":
        body = export_run_as_json_bytes(db, run_id, include_listing_detail=include_listing_detail)
        return body, "application/json", f"{run_id}{suffix}.json"
    text = export_run_as_csv_text(db, run_id, include_listing_detail=include_listing_detail)
    return text.encode("utf-8"), "text/csv; charset=utf-8", f"{run_id}{suffix}.csv"
