"""Strategy ranking using Week 2 advanced_v2 signals with request-scoped weights."""

from __future__ import annotations

from collections.abc import Sequence
from statistics import median
from typing import Any

from app.models.listing import Listing
from app.services.scoring import (
    _build_comp_index,
    _build_explanation_payload,
    _clamp,
    _confidence_signal,
    _deal_reason,
    _feature_density_signal,
    _load_scoring_config,
    _resolve_comp_context,
    _roi_proxy_signal,
    _size_value_signal,
    _time_on_market_signal,
)


def score_listing_with_strategy_weights(
    listing: Listing,
    cohort: Sequence[Listing],
    *,
    weights: dict[str, float],
    config: dict[str, Any] | None = None,
) -> tuple[float, float, str, dict[str, Any]]:
    """Return (score 0-100, confidence 0-1, deal_reason, explanation dict)."""
    cfg = config or _load_scoring_config()
    advanced_v2_cfg = cfg.get("advanced_v2", {})
    stale_inventory_days = int(cfg.get("rules", {}).get("stale_inventory_days", 90))
    fallback_order = list(
        advanced_v2_cfg.get("comps", {}).get(
            "fallback_order", ["suburb", "city", "province", "global"]
        )
    )
    include_bedrooms = bool(advanced_v2_cfg.get("comps", {}).get("include_bedrooms", True))
    include_bathrooms = bool(advanced_v2_cfg.get("comps", {}).get("include_bathrooms", True))
    minimum_cohort_size = int(advanced_v2_cfg.get("comps", {}).get("minimum_cohort_size", 12))
    roi_config = advanced_v2_cfg.get("roi", {})

    comp_index = _build_comp_index(cohort, fallback_order, include_bedrooms, include_bathrooms)
    comp_level, comparable, fallback_penalty = _resolve_comp_context(
        listing=listing,
        comp_index=comp_index,
        fallback_order=fallback_order,
        minimum_cohort_size=minimum_cohort_size,
        include_bedrooms=include_bedrooms,
        include_bathrooms=include_bathrooms,
    )

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
            _clamp(_price_deviation_signal_advanced(listing, comp_median_price) - fallback_penalty),
            4,
        )
        size_signal = round(
            _clamp(_size_value_signal(listing, comp_median_ppsqm) - fallback_penalty), 4
        )
    else:
        price_signal = 0.5
        size_signal = 0.5

    time_signal = _time_on_market_signal(listing, stale_inventory_days)
    feature_signal = _feature_density_signal(listing)
    confidence = _confidence_signal(listing)
    roi_signal = _roi_proxy_signal(listing, roi_config)

    raw_signals: dict[str, float] = {
        "price_vs_comp": price_signal,
        "size_vs_comp": size_signal,
        "time_on_market": time_signal,
        "feature_value": feature_signal,
        "confidence": confidence,
        "roi_proxy": roi_signal,
    }

    missing = set(weights) - set(raw_signals)
    if missing:
        raise ValueError(f"Strategy weights reference unknown signals: {sorted(missing)}")

    signal_values = {k: raw_signals[k] for k in weights}
    signal_weights = {k: float(weights[k]) for k in weights}
    weighted = sum(signal_weights[name] * signal_values[name] for name in signal_weights)
    score = round(_clamp(weighted) * 100.0, 2)
    deal_reason = _deal_reason(
        price_signal,
        size_signal,
        time_signal,
        feature_signal,
        confidence,
    )
    explanation = _build_explanation_payload(
        signal_values=signal_values,
        signal_weights=signal_weights,
        weighted_sum=_clamp(weighted),
        final_score=score,
        confidence=confidence,
        comp_level=comp_level,
        comp_size=len(comparable),
        fallback_order=fallback_order,
        fallback_penalty=fallback_penalty,
        roi_config=roi_config,
        listing=listing,
    )
    return score, round(confidence, 2), deal_reason, explanation


def _price_deviation_signal_advanced(listing: Listing, median_price: float) -> float:
    """Same semantics as Week 2 advanced path (median comp price)."""
    if median_price <= 0:
        return 0.5
    deviation = (median_price - listing.price) / median_price
    return round(_clamp(0.5 + deviation), 4)
