from __future__ import annotations

import hashlib
import json
from typing import Any

from app.schemas.ranking import (
    DatasetContext,
    ListingDetailResponse,
    PaginationEnvelope,
    ProfileDetailResponse,
    ProfileSummaryResponse,
    RankingQueryRequest,
    RankingQueryResponse,
    RankingResultItem,
    ResolvedProfile,
    StrategyPreset,
    TopNEnvelope,
)

PLACEHOLDER_MODEL_VERSION = "advanced_v2"
PLACEHOLDER_PROFILE_VERSION = "v1"
PLACEHOLDER_PROFILE_ID_PREFIX = "strategy-profile"

# TODO: Move profile definitions to config and evaluate strategy-specific weights.
# Keep this placeholder map only for contract-level Week 3 skeleton behavior.
_PROFILE_LIBRARY: dict[StrategyPreset, dict[str, Any]] = {
    StrategyPreset.rental_income: {
        "label": "Rental Income Focus",
        "description": "Prioritize yield and stable recurring rental performance.",
        "default_weights": {"roi_proxy": 0.35, "price_vs_comp": 0.3, "confidence": 0.15},
        "enabled_signals": ["roi_proxy", "price_vs_comp", "confidence"],
    },
    StrategyPreset.resale_arbitrage: {
        "label": "Resale/Arbitrage Focus",
        "description": "Prioritize underpriced listings with resale upside.",
        "default_weights": {"price_vs_comp": 0.45, "size_vs_comp": 0.25, "confidence": 0.1},
        "enabled_signals": ["price_vs_comp", "size_vs_comp", "confidence"],
    },
    StrategyPreset.refurbishment_value_add: {
        "label": "Refurbishment/Value-Add Focus",
        "description": "Target assets with value-add opportunity and downside control.",
        "default_weights": {"price_vs_comp": 0.4, "feature_value": 0.25, "confidence": 0.15},
        "enabled_signals": ["price_vs_comp", "feature_value", "confidence"],
    },
    StrategyPreset.balanced_long_term: {
        "label": "Balanced Long-Term Hold",
        "description": "Balanced blend of yield, comparables, and confidence.",
        "default_weights": {"roi_proxy": 0.25, "price_vs_comp": 0.25, "confidence": 0.2},
        "enabled_signals": ["roi_proxy", "price_vs_comp", "confidence"],
    },
}


def _stable_json_hash(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:12]


def _safe_override_bounds(default_weights: dict[str, float]) -> dict[str, dict[str, float]]:
    bounds: dict[str, dict[str, float]] = {}
    for signal, weight in default_weights.items():
        bounds[signal] = {
            "min": round(max(0.0, weight * 0.8), 6),
            "max": round(min(1.0, weight * 1.2), 6),
        }
    return bounds


def _normalized_weights(
    default_weights: dict[str, float], overrides: dict[str, float]
) -> dict[str, float]:
    merged = dict(default_weights)
    merged.update(overrides)
    total = sum(merged.values())
    if total <= 0:
        raise ValueError("Resolved profile weights must sum to a positive value.")
    return {signal: round(weight / total, 6) for signal, weight in merged.items()}


def list_profiles() -> list[ProfileSummaryResponse]:
    return [
        ProfileSummaryResponse(
            preset=preset,
            label=profile["label"],
            description=profile["description"],
        )
        for preset, profile in _PROFILE_LIBRARY.items()
    ]


def resolve_profile(
    preset: StrategyPreset, weight_overrides: dict[str, float] | None = None
) -> ProfileDetailResponse:
    profile = _PROFILE_LIBRARY[preset]
    default_weights: dict[str, float] = profile["default_weights"]
    safe_bounds = _safe_override_bounds(default_weights)
    requested_overrides = weight_overrides or {}

    invalid_signals = set(requested_overrides) - set(default_weights)
    if invalid_signals:
        invalid = ", ".join(sorted(invalid_signals))
        raise ValueError(f"Unknown override signal(s): {invalid}")

    for signal, value in requested_overrides.items():
        bounds = safe_bounds[signal]
        if value < bounds["min"] or value > bounds["max"]:
            range_message = (
                f"Override for '{signal}' must be between "
                f"{bounds['min']} and {bounds['max']}, got {value}."
            )
            raise ValueError(range_message)

    normalized = _normalized_weights(default_weights, requested_overrides)
    return ProfileDetailResponse(
        preset=preset,
        profile_id=f"{PLACEHOLDER_PROFILE_ID_PREFIX}-{preset.value}",
        profile_version=PLACEHOLDER_PROFILE_VERSION,
        default_weights=normalized,
        enabled_signals=profile["enabled_signals"],
        safe_override_bounds=safe_bounds,
    )


def run_ranking_query(request: RankingQueryRequest) -> RankingQueryResponse:
    request_payload = request.model_dump(mode="json")
    query_fingerprint = _stable_json_hash(request_payload)
    run_id = f"placeholder-run-{query_fingerprint}"

    profile = resolve_profile(request.strategy.preset, request.strategy.weight_overrides)
    resolved_profile = ResolvedProfile(
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        resolved_weights=profile.default_weights,
        enabled_signals=profile.enabled_signals,
    )

    result_item = RankingResultItem(
        listing_id=100001,
        score=78.5,
        deal_reason="Placeholder ranking result for Week 3 contract validation.",
        confidence=0.82,
        summary={
            "price": 2350000,
            "city": request.filters.city or "Cape Town",
            "suburb": request.filters.suburb or "Unknown",
            "property_type": request.filters.property_type or "House",
        },
        detail_ref=f"{run_id}:listing-100001",
    )
    results = [result_item]

    dataset_context = DatasetContext(
        selected_sources=request.dataset_sources,
        records_considered=len(request.dataset_sources) * 100,
        last_ingested_at="2026-04-28T10:00:00Z",
        last_scored_at="2026-04-28T10:05:00Z",
        model_version=PLACEHOLDER_MODEL_VERSION,
        profile_version=resolved_profile.profile_version,
    )

    pagination = None
    top_n = None
    if request.result_window.top_n is not None:
        top_n_requested = request.result_window.top_n
        top_n = TopNEnvelope(
            mode="top_n",
            top_n_requested=top_n_requested,
            top_n_returned=min(top_n_requested, len(results)),
        )
    else:
        page = request.result_window.page or 1
        page_size = request.result_window.page_size or 20
        pagination = PaginationEnvelope(
            mode="pagination",
            page=page,
            page_size=page_size,
            total_count=len(results),
        )

    return RankingQueryResponse(
        run_id=run_id,
        query_fingerprint=query_fingerprint,
        resolved_profile=resolved_profile,
        dataset_context=dataset_context,
        results=results,
        pagination=pagination,
        top_n=top_n,
    )


def get_listing_detail(run_id: str, listing_id: int) -> ListingDetailResponse:
    return ListingDetailResponse(
        listing_core={
            "run_id": run_id,
            "listing_id": listing_id,
            "price": 2350000,
            "location": "Placeholder Suburb, Cape Town",
            "property_type": "House",
        },
        score_summary={
            "score": 78.5,
            "deal_reason": "Placeholder detail response for contract iteration.",
            "model_version": PLACEHOLDER_MODEL_VERSION,
            "profile_version": PLACEHOLDER_PROFILE_VERSION,
        },
        diagnostics={
            "signals": [
                {
                    "name": "price_vs_comp",
                    "raw": 0.73,
                    "normalized": 0.73,
                    "weighted": 0.24,
                },
                {
                    "name": "roi_proxy",
                    "raw": 0.69,
                    "normalized": 0.69,
                    "weighted": 0.2,
                },
            ],
            "risk_flags": [],
            "detail_ref": f"{run_id}:listing-{listing_id}",
        },
    )
