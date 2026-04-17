from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import median
from typing import Any

import yaml
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing
from app.models.score_result import ScoreResult

DEFAULT_SCORING_CONFIG: dict[str, Any] = {
    "weights": {
        "price_deviation": 0.35,
        "time_on_market": 0.2,
        "feature_value": 0.2,
        "liquidity": 0.15,
        "confidence": 0.1,
    },
    "rules": {
        "stale_inventory_days": 90,
        "minimum_confidence": 0.6,
        "outlier_zscore_threshold": 2.5,
    },
    "flags": {
        "enable_liquidity_signal": True,
        "enable_feature_signal": True,
        "enable_explanation_payload": True,
        "enable_advanced_v2_roi_proxy": False,
        "enable_advanced_v2_micro_comps": False,
    },
    "advanced_v2": {
        "comps": {
            "minimum_cohort_size": 12,
            "fallback_order": ["suburb", "city", "province", "global"],
            "include_bedrooms": True,
            "include_bathrooms": True,
        },
        "roi": {
            # Heuristic defaults for MVP; calibrate per market/dataset later.
            "transaction_cost_pct": 0.08,
            "vacancy_allowance_pct": 0.05,
            "maintenance_pct": 0.04,
            "management_pct": 0.08,
            "insurance_pct": 0.01,
        },
    },
    "evaluation_thresholds": {
        "top20_jaccard_min": 0.7,
        "rank_correlation_min": 0.8,
    },
}


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _deep_merge_dict(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key, default_value in defaults.items():
        override_value = overrides.get(key)
        if isinstance(default_value, dict) and isinstance(override_value, dict):
            merged[key] = _deep_merge_dict(default_value, override_value)
        elif key in overrides:
            merged[key] = override_value
        else:
            merged[key] = default_value

    for key, override_value in overrides.items():
        if key not in merged:
            merged[key] = override_value
    return merged


def _load_scoring_config() -> dict[str, Any]:
    candidate_paths = [
        Path("config/scoring.yaml"),
        Path("../config/scoring.yaml"),
    ]
    for path in candidate_paths:
        if path.exists():
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return _deep_merge_dict(DEFAULT_SCORING_CONFIG, loaded)
    return deepcopy(DEFAULT_SCORING_CONFIG)


def _days_on_market(date_posted: date | None) -> int | None:
    if date_posted is None:
        return None
    return max(0, (datetime.now(UTC).date() - date_posted).days)


def _confidence_signal(listing: Listing) -> float:
    tracked_fields = [
        listing.date_posted,
        listing.floor_size,
        listing.erf_size,
        listing.listing_id,
        listing.source_site,
        listing.city,
        listing.province,
        listing.agent_name,
    ]
    present = sum(1 for value in tracked_fields if value not in (None, "", 0))
    return round(_clamp(present / len(tracked_fields)), 4)


def _feature_density_signal(listing: Listing) -> float:
    bedrooms_score = _clamp((listing.bedrooms or 0) / 6.0)
    bathrooms_score = _clamp((listing.bathrooms or 0.0) / 4.0)
    size_score = _clamp((listing.floor_size or 0.0) / 250.0)
    return round((bedrooms_score + bathrooms_score + size_score) / 3.0, 4)


def _size_value_signal(listing: Listing, median_price_per_sqm: float) -> float:
    if listing.floor_size is None or listing.floor_size <= 0:
        return 0.5
    listing_ppsqm = listing.price / listing.floor_size
    if median_price_per_sqm <= 0:
        return 0.5
    # Lower than area median is better for deal score.
    deviation = (median_price_per_sqm - listing_ppsqm) / median_price_per_sqm
    return round(_clamp(0.5 + deviation), 4)


def _time_on_market_signal(listing: Listing, stale_inventory_days: int) -> float:
    days = _days_on_market(listing.date_posted)
    if days is None:
        return 0.5
    if stale_inventory_days <= 0:
        return 0.5
    return round(_clamp(days / stale_inventory_days), 4)


def _price_deviation_signal(listing: Listing, median_price: float) -> float:
    if median_price <= 0:
        return 0.5
    deviation = (median_price - listing.price) / median_price
    return round(_clamp(0.5 + deviation), 4)


def _deal_reason(
    price_signal: float,
    size_signal: float,
    time_signal: float,
    feature_signal: float,
    confidence_signal: float,
) -> str:
    reasons: list[str] = []

    if price_signal >= 0.65:
        reasons.append("Price is favorable versus dataset median")
    if size_signal >= 0.65:
        reasons.append("Strong size-to-price profile")
    if time_signal >= 0.65:
        reasons.append("Extended time on market may indicate seller pressure")
    if feature_signal >= 0.65:
        reasons.append("Feature density supports value")
    if confidence_signal < 0.5:
        reasons.append("Limited metadata reduced confidence")

    if not reasons:
        reasons.append("Baseline composite score from normalized listing attributes")

    return "; ".join(reasons[:3])


def run_scoring_job(db: Session, job_id: int) -> IngestionJob:
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise ValueError(f"Ingestion job not found: {job_id}")

    listings = db.scalars(select(Listing).where(Listing.job_id == job_id)).all()
    if not listings:
        raise ValueError(f"No listings found for ingestion job: {job_id}")

    config = _load_scoring_config()
    weights = config["weights"]
    stale_inventory_days = int(config["rules"]["stale_inventory_days"])

    prices = [listing.price for listing in listings if listing.price is not None]
    price_per_sqm_values = [
        listing.price / listing.floor_size
        for listing in listings
        if listing.floor_size is not None and listing.floor_size > 0
    ]
    median_price = float(median(prices)) if prices else 0.0
    median_price_per_sqm = float(median(price_per_sqm_values)) if price_per_sqm_values else 0.0

    db.execute(delete(ScoreResult).where(ScoreResult.job_id == job_id))

    for listing in listings:
        price_signal = _price_deviation_signal(listing, median_price)
        size_signal = _size_value_signal(listing, median_price_per_sqm)
        time_signal = _time_on_market_signal(listing, stale_inventory_days)
        feature_signal = _feature_density_signal(listing)
        confidence = _confidence_signal(listing)

        weighted = (
            weights["price_deviation"] * price_signal
            + weights["feature_value"] * size_signal
            + weights["time_on_market"] * time_signal
            + weights["liquidity"] * feature_signal
            + weights["confidence"] * confidence
        )
        score = round(_clamp(weighted) * 100.0, 2)

        db.add(
            ScoreResult(
                job_id=job_id,
                listing_id=listing.id,
                score=score,
                confidence=round(confidence, 2),
                deal_reason=_deal_reason(
                    price_signal=price_signal,
                    size_signal=size_signal,
                    time_signal=time_signal,
                    feature_signal=feature_signal,
                    confidence_signal=confidence,
                ),
                model_version="baseline_v1",
            )
        )

    if job.status == "processing":
        job.status = "completed"
    db.commit()
    db.refresh(job)
    return job
