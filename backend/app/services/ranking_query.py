from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ranking_run import RankingRun
from app.models.scoring_profile_backup import ScoringProfileBackup
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
SUPPORTED_SIGNALS = {
    "price_vs_comp",
    "size_vs_comp",
    "time_on_market",
    "feature_value",
    "confidence",
    "roi_proxy",
}


def _stable_json_hash(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:12]


def _stable_json_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


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


def _load_scoring_profiles_config() -> dict[str, Any]:
    candidate_paths: list[Path] = []
    configured_path = os.getenv("SCORING_PROFILES_PATH")
    if configured_path:
        candidate_paths.append(Path(configured_path))
    candidate_paths.extend(
        [
            Path("backend/config/scoring_profiles.yaml"),
            Path("config/scoring_profiles.yaml"),
            Path(__file__).resolve().parents[2] / "config/scoring_profiles.yaml",
        ]
    )

    for path in candidate_paths:
        if path.exists():
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(loaded, dict):
                raise ValueError("scoring_profiles.yaml must be a mapping at the root.")
            return loaded
    raise ValueError("No scoring profile config found at backend/config/scoring_profiles.yaml.")


def _validate_profile_definition(
    profile_id: str, profile: dict[str, Any]
) -> tuple[dict[str, float], list[str]]:
    configured_profile_id = profile.get("profile_id")
    if not isinstance(configured_profile_id, str) or not configured_profile_id:
        raise ValueError(f"Profile '{profile_id}' must define profile_id.")
    if configured_profile_id != profile_id:
        raise ValueError(
            f"Profile key '{profile_id}' must match profile_id '{configured_profile_id}'."
        )

    weights_raw = profile.get("weights")
    enabled_signals_raw = profile.get("enabled_signals")
    if not isinstance(weights_raw, dict) or not weights_raw:
        raise ValueError(f"Profile '{profile_id}' must define non-empty weights.")
    if not isinstance(enabled_signals_raw, list) or not enabled_signals_raw:
        raise ValueError(f"Profile '{profile_id}' must define enabled_signals.")

    weights: dict[str, float] = {str(k): float(v) for k, v in weights_raw.items()}
    enabled_signals = [str(signal) for signal in enabled_signals_raw]
    unknown_signals = set(weights) | set(enabled_signals)
    unknown_signals = unknown_signals - SUPPORTED_SIGNALS
    if unknown_signals:
        raise ValueError(
            f"Profile '{profile_id}' references unsupported signal(s): "
            f"{', '.join(sorted(unknown_signals))}"
        )

    enabled_set = set(enabled_signals)
    if set(weights) != enabled_set:
        raise ValueError(f"Profile '{profile_id}' weights must exactly match enabled_signals.")
    if any(weight <= 0 for weight in weights.values()):
        raise ValueError(f"Profile '{profile_id}' weights must be positive.")
    return weights, enabled_signals


def _get_profile_config(preset: StrategyPreset) -> tuple[str, dict[str, Any]]:
    config = _load_scoring_profiles_config()
    profiles = config.get("profiles")
    preset_alias_mapping = config.get("preset_alias_mapping")
    if not isinstance(profiles, dict):
        raise ValueError("scoring_profiles config must define a 'profiles' mapping.")
    if not isinstance(preset_alias_mapping, dict):
        raise ValueError("scoring_profiles config must define a 'preset_alias_mapping' mapping.")

    profile_id = preset_alias_mapping.get(preset.value)
    if not isinstance(profile_id, str) or not profile_id:
        raise ValueError(f"No profile mapping configured for preset '{preset.value}'.")

    profile = profiles.get(profile_id)
    if not isinstance(profile, dict):
        raise ValueError(f"Preset '{preset.value}' maps to missing profile '{profile_id}'.")
    return profile_id, profile


def list_profiles() -> list[ProfileSummaryResponse]:
    config = _load_scoring_profiles_config()
    alias_mapping = config.get("preset_alias_mapping", {})
    profiles = config.get("profiles", {})
    responses: list[ProfileSummaryResponse] = []
    for preset in StrategyPreset:
        profile_id = alias_mapping.get(preset.value)
        if not isinstance(profile_id, str):
            raise ValueError(f"No profile mapping configured for preset '{preset.value}'.")
        profile = profiles.get(profile_id)
        if not isinstance(profile, dict):
            raise ValueError(f"Preset '{preset.value}' maps to missing profile '{profile_id}'.")
        responses.append(
            ProfileSummaryResponse(
                preset=preset,
                label=str(profile.get("label", profile_id)),
                description=str(profile.get("description", "")),
            )
        )
    return responses


def resolve_profile(
    preset: StrategyPreset, weight_overrides: dict[str, float] | None = None
) -> ProfileDetailResponse:
    profile_id, profile = _get_profile_config(preset)
    configured_weights, enabled_signals = _validate_profile_definition(profile_id, profile)
    default_weights = _normalized_weights(configured_weights, {})
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
        profile_id=profile_id,
        profile_version=PLACEHOLDER_PROFILE_VERSION,
        default_weights=normalized,
        enabled_signals=enabled_signals,
        safe_override_bounds=safe_bounds,
    )


def _persist_ranking_run(
    db: Session,
    *,
    run_id: str,
    query_fingerprint: str,
    request_payload: dict[str, Any],
    profile: ProfileDetailResponse,
    result_count: int,
) -> None:
    profile_payload = {
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
        "enabled_signals": profile.enabled_signals,
        "default_weights": profile.default_weights,
        "safe_override_bounds": profile.safe_override_bounds,
    }
    profile_fingerprint = _stable_json_digest(profile_payload)
    backup = db.scalar(
        select(ScoringProfileBackup).where(
            ScoringProfileBackup.profile_fingerprint == profile_fingerprint
        )
    )
    if backup is None:
        backup = ScoringProfileBackup(
            profile_id=profile.profile_id,
            profile_fingerprint=profile_fingerprint,
            profile_payload=profile_payload,
        )
        db.add(backup)
        db.flush()

    db.add(
        RankingRun(
            run_id=run_id,
            query_fingerprint=query_fingerprint,
            strategy_preset=request_payload["strategy"]["preset"],
            resolved_profile_id=profile.profile_id,
            profile_row_id=backup.id,
            request_payload=request_payload,
            result_window=request_payload["result_window"],
            result_count=result_count,
        )
    )
    db.commit()


def run_ranking_query(
    request: RankingQueryRequest, db: Session | None = None
) -> RankingQueryResponse:
    request_payload = request.model_dump(mode="json")
    query_fingerprint = _stable_json_hash(request_payload)
    run_id = f"run-{uuid4().hex[:12]}"

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

    if db is not None:
        _persist_ranking_run(
            db,
            run_id=run_id,
            query_fingerprint=query_fingerprint,
            request_payload=request_payload,
            profile=profile,
            result_count=len(results),
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
