from __future__ import annotations

import os
from collections.abc import Sequence
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
        "weights": {
            "price_vs_comp": 0.3,
            "size_vs_comp": 0.18,
            "time_on_market": 0.14,
            "feature_value": 0.1,
            "confidence": 0.08,
            "roi_proxy": 0.2,
        },
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
        "data_quality": {
            "valid_rate_min": 0.85,
            "duplicate_rate_max": 0.05,
            "price_null_rate_max": 0.10,
        },
        "scoring_sanity": {
            "score_min": 0.0,
            "score_max": 100.0,
            "signal_dominance_cap": 0.70,
            "high_score_cutoff": 80.0,
        },
        "stability": {
            "segments": {
                "top_band": {
                    "mode": "top_n",
                    "top_n": 20,
                    "jaccard_min": 0.7,
                    "rank_correlation_min": 0.8,
                    "perturbation_overlap_min": 0.6,
                    "median_abs_rank_shift_pct_max": 0.15,
                    "p90_rank_shift_pct_max": 0.60,
                },
                "middle_band": {
                    "start_pct": 0.45,
                    "end_pct": 0.60,
                    "jaccard_warn_min": 0.3,
                    "rank_correlation_warn_min": 0.5,
                    "median_abs_rank_shift_pct_warn_max": 0.45,
                    "p90_rank_shift_pct_warn_max": 0.85,
                },
                "bottom_band": {
                    "start_pct": 0.85,
                    "end_pct": 1.00,
                    "jaccard_warn_min": 0.25,
                    "rank_correlation_warn_min": 0.4,
                    "median_abs_rank_shift_pct_warn_max": 0.50,
                    "p90_rank_shift_pct_warn_max": 0.90,
                },
            },
            "full_dataset": {
                "median_abs_rank_shift_pct_warn_max": 0.35,
                "p90_rank_shift_pct_warn_max": 0.80,
            },
        },
        "decision": {
            "minimum_sample_for_promote": 100,
        },
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
    candidate_paths: list[Path] = []
    configured_path = os.getenv("SCORING_CONFIG_PATH")
    if configured_path:
        candidate_paths.append(Path(configured_path))
    candidate_paths.extend(
        [
            Path("config/scoring.yaml"),
            Path("../config/scoring.yaml"),
            Path("/config/scoring.yaml"),
            Path("/workspace/config/scoring.yaml"),
            Path(__file__).resolve().parents[2] / "config/scoring.yaml",
        ]
    )

    seen: set[Path] = set()
    for path in candidate_paths:
        if path in seen:
            continue
        seen.add(path)
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


def _normalize_location(value: str | None) -> str:
    return (value or "").strip().lower()


def _bath_bucket(value: float | None) -> int:
    return int(round(value or 0.0))


def _comp_key_for_level(
    listing: Listing,
    level: str,
    include_bedrooms: bool,
    include_bathrooms: bool,
) -> tuple[Any, ...]:
    base: list[Any] = []
    if level == "suburb":
        base.extend(
            [
                _normalize_location(listing.province),
                _normalize_location(listing.city),
                _normalize_location(listing.suburb),
            ]
        )
    elif level == "city":
        base.extend([_normalize_location(listing.province), _normalize_location(listing.city)])
    elif level == "province":
        base.append(_normalize_location(listing.province))
    elif level == "global":
        base.append("global")
    else:
        base.append(level)

    base.append((listing.property_type or "").strip().lower())
    if include_bedrooms:
        base.append(int(listing.bedrooms or 0))
    if include_bathrooms:
        base.append(_bath_bucket(listing.bathrooms))
    return tuple(base)


def _build_comp_index(
    listings: Sequence[Listing],
    fallback_order: list[str],
    include_bedrooms: bool,
    include_bathrooms: bool,
) -> dict[str, dict[tuple[Any, ...], list[Listing]]]:
    index: dict[str, dict[tuple[Any, ...], list[Listing]]] = {level: {} for level in fallback_order}
    for listing in listings:
        for level in fallback_order:
            key = _comp_key_for_level(listing, level, include_bedrooms, include_bathrooms)
            index[level].setdefault(key, []).append(listing)
    return index


def _fallback_penalty(level: str) -> float:
    penalties = {"suburb": 0.0, "city": 0.03, "province": 0.06, "global": 0.1}
    return penalties.get(level, 0.1)


def _resolve_comp_context(
    listing: Listing,
    comp_index: dict[str, dict[tuple[Any, ...], list[Listing]]],
    fallback_order: list[str],
    minimum_cohort_size: int,
    include_bedrooms: bool,
    include_bathrooms: bool,
) -> tuple[str | None, list[Listing], float]:
    for level in fallback_order:
        key = _comp_key_for_level(listing, level, include_bedrooms, include_bathrooms)
        cohort = comp_index.get(level, {}).get(key, [])
        # Anti-leakage safeguard: do not include the listing itself in its comp cohort.
        comparable = [row for row in cohort if row.id != listing.id]
        if len(comparable) >= minimum_cohort_size:
            return level, comparable, _fallback_penalty(level)

    return None, [], 0.0


def _gross_yield_assumption(property_type: str | None) -> float:
    normalized = (property_type or "").strip().lower()
    if "apartment" in normalized or "flat" in normalized:
        return 0.09
    if "townhouse" in normalized or "duplex" in normalized:
        return 0.082
    if "vacant" in normalized or "land" in normalized:
        return 0.0
    return 0.075


def _roi_proxy_signal(listing: Listing, roi_config: dict[str, Any]) -> float:
    if listing.price is None or listing.price <= 0:
        return 0.5

    transaction_cost_pct = float(roi_config.get("transaction_cost_pct", 0.08))
    vacancy_allowance_pct = float(roi_config.get("vacancy_allowance_pct", 0.05))
    maintenance_pct = float(roi_config.get("maintenance_pct", 0.04))
    management_pct = float(roi_config.get("management_pct", 0.08))
    insurance_pct = float(roi_config.get("insurance_pct", 0.01))

    effective_purchase_price = listing.price * (1.0 + transaction_cost_pct)
    annual_rent = listing.price * _gross_yield_assumption(listing.property_type)

    fixed_monthly_costs = float(listing.rates_and_taxes or 0.0) + float(listing.levies or 0.0)
    annual_fixed_costs = fixed_monthly_costs * 12.0
    annual_variable_costs = annual_rent * (vacancy_allowance_pct + management_pct)
    annual_asset_costs = effective_purchase_price * (maintenance_pct + insurance_pct)
    annual_costs = annual_fixed_costs + annual_variable_costs + annual_asset_costs

    if effective_purchase_price > 0:
        net_yield = (annual_rent - annual_costs) / effective_purchase_price
    else:
        net_yield = 0.0
    # Normalize around practical residential ranges; 6% net yield ~= neutral 0.5.
    normalized = 0.5 + (net_yield - 0.06) / 0.12
    return round(_clamp(normalized), 4)


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


def _build_explanation_payload(
    *,
    signal_values: dict[str, float],
    signal_weights: dict[str, float],
    weighted_sum: float,
    final_score: float,
    confidence: float,
    comp_level: str | None,
    comp_size: int,
    fallback_order: list[str],
    fallback_penalty: float,
    roi_config: dict[str, Any],
    listing: Listing,
) -> dict[str, Any]:
    signal_rows: list[dict[str, Any]] = []
    for name, normalized_score in signal_values.items():
        weight = float(signal_weights.get(name, 0.0))
        signal_rows.append(
            {
                "name": name,
                "raw_value": round(normalized_score, 6),
                "normalized_score": round(normalized_score, 6),
                "weight": round(weight, 6),
                "weighted_contribution": round(normalized_score * weight, 6),
            }
        )

    signal_rows.sort(key=lambda row: row["weighted_contribution"], reverse=True)
    primary_driver = signal_rows[0]["name"] if signal_rows else "none"
    confidence_note = (
        "Limited metadata reduced confidence"
        if confidence < 0.5
        else "Data completeness acceptable"
    )

    missing_fields: list[str] = []
    if listing.price is None:
        missing_fields.append("price")
    if listing.floor_size is None or listing.floor_size <= 0:
        missing_fields.append("floor_size")
    if listing.date_posted is None:
        missing_fields.append("date_posted")

    risk_flags: list[str] = []
    if confidence < 0.5:
        risk_flags.append("low_confidence")

    fallbacks_used: list[str] = []
    if comp_level in {"city", "province", "global"}:
        fallbacks_used.append(comp_level)

    return {
        "summary": {
            "primary_driver": primary_driver,
            "confidence_note": confidence_note,
            "fallbacks_used": fallbacks_used,
        },
        "signals": signal_rows,
        "score_math": {
            "weighted_sum_0_to_1": round(weighted_sum, 6),
            "final_score_0_to_100": round(final_score, 2),
        },
        "comps_context": {
            "segment_level": comp_level,
            "cohort_size": comp_size,
            "fallback_path": fallback_order,
            "fallback_penalty": round(fallback_penalty, 6),
        },
        "roi_assumptions": {
            "transaction_cost_pct": float(roi_config.get("transaction_cost_pct", 0.08)),
            "vacancy_allowance_pct": float(roi_config.get("vacancy_allowance_pct", 0.05)),
            "maintenance_pct": float(roi_config.get("maintenance_pct", 0.04)),
            "management_pct": float(roi_config.get("management_pct", 0.08)),
            "insurance_pct": float(roi_config.get("insurance_pct", 0.01)),
        },
        "risk_flags": risk_flags,
        "missing_fields": missing_fields,
    }


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
    flags = config.get("flags", {})
    advanced_v2_enabled = bool(
        flags.get("enable_advanced_v2_micro_comps") or flags.get("enable_advanced_v2_roi_proxy")
    )
    advanced_v2_cfg = config.get("advanced_v2", {})
    advanced_weights = advanced_v2_cfg.get("weights", {})

    fallback_order = list(
        advanced_v2_cfg.get("comps", {}).get(
            "fallback_order", ["suburb", "city", "province", "global"]
        )
    )
    include_bedrooms = bool(advanced_v2_cfg.get("comps", {}).get("include_bedrooms", True))
    include_bathrooms = bool(advanced_v2_cfg.get("comps", {}).get("include_bathrooms", True))
    minimum_cohort_size = int(advanced_v2_cfg.get("comps", {}).get("minimum_cohort_size", 12))
    roi_config = advanced_v2_cfg.get("roi", {})
    comp_index = (
        _build_comp_index(listings, fallback_order, include_bedrooms, include_bathrooms)
        if advanced_v2_enabled
        else {}
    )

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
        comp_level: str | None = None
        comp_size = 0
        fallback_penalty = 0.0
        if advanced_v2_enabled:
            comp_level, comparable, fallback_penalty = _resolve_comp_context(
                listing=listing,
                comp_index=comp_index,
                fallback_order=fallback_order,
                minimum_cohort_size=minimum_cohort_size,
                include_bedrooms=include_bedrooms,
                include_bathrooms=include_bathrooms,
            )
            comp_size = len(comparable)
            if comparable:
                comp_prices = [row.price for row in comparable if row.price is not None]
                comp_ppsqm = [
                    row.price / row.floor_size
                    for row in comparable
                    if row.floor_size is not None and row.floor_size > 0 and row.price is not None
                ]
                comp_median_price = float(median(comp_prices)) if comp_prices else 0.0
                comp_median_ppsqm = float(median(comp_ppsqm)) if comp_ppsqm else 0.0
                price_signal = round(
                    _clamp(_price_deviation_signal(listing, comp_median_price) - fallback_penalty),
                    4,
                )
                size_signal = round(
                    _clamp(_size_value_signal(listing, comp_median_ppsqm) - fallback_penalty), 4
                )
            else:
                price_signal = 0.5
                size_signal = 0.5
        else:
            price_signal = _price_deviation_signal(listing, median_price)
            size_signal = _size_value_signal(listing, median_price_per_sqm)

        time_signal = _time_on_market_signal(listing, stale_inventory_days)
        feature_signal = _feature_density_signal(listing)
        confidence = _confidence_signal(listing)
        roi_signal = (
            _roi_proxy_signal(listing, roi_config)
            if flags.get("enable_advanced_v2_roi_proxy")
            else 0.5
        )

        if advanced_v2_enabled:
            signal_values = {
                "price_vs_comp": price_signal,
                "size_vs_comp": size_signal,
                "time_on_market": time_signal,
                "feature_value": feature_signal,
                "confidence": confidence,
                "roi_proxy": roi_signal,
            }
            signal_weights = {
                "price_vs_comp": float(advanced_weights.get("price_vs_comp", 0.3)),
                "size_vs_comp": float(advanced_weights.get("size_vs_comp", 0.18)),
                "time_on_market": float(advanced_weights.get("time_on_market", 0.14)),
                "feature_value": float(advanced_weights.get("feature_value", 0.1)),
                "confidence": float(advanced_weights.get("confidence", 0.08)),
                "roi_proxy": float(advanced_weights.get("roi_proxy", 0.2)),
            }
            weighted = (
                float(advanced_weights.get("price_vs_comp", 0.3)) * price_signal
                + float(advanced_weights.get("size_vs_comp", 0.18)) * size_signal
                + float(advanced_weights.get("time_on_market", 0.14)) * time_signal
                + float(advanced_weights.get("feature_value", 0.1)) * feature_signal
                + float(advanced_weights.get("confidence", 0.08)) * confidence
                + float(advanced_weights.get("roi_proxy", 0.2)) * roi_signal
            )
        else:
            signal_values = {
                "price_deviation": price_signal,
                "feature_value": size_signal,
                "time_on_market": time_signal,
                "liquidity": feature_signal,
                "confidence": confidence,
            }
            signal_weights = {
                "price_deviation": float(weights["price_deviation"]),
                "feature_value": float(weights["feature_value"]),
                "time_on_market": float(weights["time_on_market"]),
                "liquidity": float(weights["liquidity"]),
                "confidence": float(weights["confidence"]),
            }
            weighted = (
                weights["price_deviation"] * price_signal
                + weights["feature_value"] * size_signal
                + weights["time_on_market"] * time_signal
                + weights["liquidity"] * feature_signal
                + weights["confidence"] * confidence
            )
        score = round(_clamp(weighted) * 100.0, 2)
        explanation = _build_explanation_payload(
            signal_values=signal_values,
            signal_weights=signal_weights,
            weighted_sum=_clamp(weighted),
            final_score=score,
            confidence=confidence,
            comp_level=comp_level,
            comp_size=comp_size,
            fallback_order=fallback_order,
            fallback_penalty=fallback_penalty,
            roi_config=roi_config,
            listing=listing,
        )

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
                explanation=explanation,
                model_version="advanced_v2" if advanced_v2_enabled else "baseline_v1",
            )
        )

    if job.status == "processing":
        job.status = "completed"
    db.commit()
    db.refresh(job)
    return job
