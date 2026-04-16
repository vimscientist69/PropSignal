from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset_validation_result import DatasetValidationResult
from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing
from app.models.raw_listing import RawListing
from app.models.rejected_listing import RejectedListing

FAIL_VALID_RATE_THRESHOLD = 0.70
WARN_PRICE_NULL_RATE_THRESHOLD = 0.10
WARN_DUPLICATE_RATE_THRESHOLD = 0.05


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _numeric_stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "max": None, "median": None}
    return {
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "median": round(float(median(values)), 2),
    }


def _parse_rejection_detail(error_detail: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(error_detail)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def run_dataset_validation(db: Session, job_id: int) -> DatasetValidationResult:
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise ValueError(f"Ingestion job not found: {job_id}")

    raw_rows = db.scalars(select(RawListing).where(RawListing.job_id == job_id)).all()
    rejected_rows = db.scalars(
        select(RejectedListing).where(RejectedListing.job_id == job_id)
    ).all()
    listings = db.scalars(select(Listing).where(Listing.job_id == job_id)).all()

    total = job.records_total
    valid = job.records_valid
    invalid = job.records_invalid

    valid_rate = _safe_rate(valid, total)
    invalid_rate = _safe_rate(invalid, total)

    duplicate_candidates = [
        (row.source_site, row.listing_id)
        for row in raw_rows
        if row.source_site not in (None, "") and row.listing_id not in (None, "")
    ]
    duplicate_counter = Counter(duplicate_candidates)
    duplicate_records = sum(count - 1 for count in duplicate_counter.values() if count > 1)
    duplicate_rate = _safe_rate(duplicate_records, total)

    price_null_count = sum(
        1 for row in raw_rows if isinstance(row.payload, dict) and row.payload.get("price") is None
    )
    price_null_rate = _safe_rate(price_null_count, total)

    rejection_codes = Counter(row.error_code for row in rejected_rows)
    rejection_types: Counter[str] = Counter()
    rejection_fields: Counter[str] = Counter()
    for row in rejected_rows:
        for error in _parse_rejection_detail(row.error_detail):
            error_type = error.get("type")
            if isinstance(error_type, str):
                rejection_types[error_type] += 1
            loc = error.get("loc")
            field = loc[0] if isinstance(loc, list) and loc else "<root>"
            rejection_fields[str(field)] += 1

    if total == 0 or valid_rate < FAIL_VALID_RATE_THRESHOLD:
        status = "fail"
    elif (
        price_null_rate > WARN_PRICE_NULL_RATE_THRESHOLD
        or duplicate_rate > WARN_DUPLICATE_RATE_THRESHOLD
    ):
        status = "warn"
    else:
        status = "pass"

    report = {
        "job_id": job_id,
        "status": status,
        "counts": {"total": total, "valid": valid, "invalid": invalid},
        "rates": {
            "valid_rate": valid_rate,
            "invalid_rate": invalid_rate,
            "duplicate_rate": duplicate_rate,
            "price_null_rate": price_null_rate,
        },
        "thresholds": {
            "fail_valid_rate_below": FAIL_VALID_RATE_THRESHOLD,
            "warn_price_null_rate_above": WARN_PRICE_NULL_RATE_THRESHOLD,
            "warn_duplicate_rate_above": WARN_DUPLICATE_RATE_THRESHOLD,
        },
        "rejections": {
            "by_error_code": dict(rejection_codes),
            "by_error_type": dict(rejection_types),
            "top_fields": dict(rejection_fields.most_common(10)),
        },
        "numeric_summary": {
            "price": _numeric_stats([float(listing.price) for listing in listings]),
            "bedrooms": _numeric_stats([float(listing.bedrooms) for listing in listings]),
            "bathrooms": _numeric_stats([float(listing.bathrooms) for listing in listings]),
            "floor_size": _numeric_stats(
                [
                    float(listing.floor_size)
                    for listing in listings
                    if listing.floor_size is not None
                ]
            ),
        },
    }

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"job_{job_id}_validation.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    existing = db.scalar(
        select(DatasetValidationResult).where(DatasetValidationResult.job_id == job_id)
    )
    if existing is None:
        result = DatasetValidationResult(
            job_id=job_id,
            status=status,
            valid_rate=valid_rate,
            invalid_rate=invalid_rate,
            duplicate_rate=duplicate_rate,
            price_null_rate=price_null_rate,
            summary=report,
            report_path=str(report_path),
        )
        db.add(result)
    else:
        existing.status = status
        existing.valid_rate = valid_rate
        existing.invalid_rate = invalid_rate
        existing.duplicate_rate = duplicate_rate
        existing.price_null_rate = price_null_rate
        existing.summary = report
        existing.report_path = str(report_path)
        result = existing

    db.commit()
    db.refresh(result)
    return result
