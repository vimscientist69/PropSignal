from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing
from app.models.ranking_run import RankingRun
from app.models.ranking_run_listing import RankingRunListing
from app.models.score_result import ScoreResult
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
from app.services.dataset_sources import merge_listings_for_jobs, resolve_dataset_sources_to_job_ids
from app.services.listing_serialization import listing_columns_public_dict
from app.services.ranking_filters import apply_ranking_filters
from app.services.ranking_signals import score_listing_with_strategy_weights

PLACEHOLDER_PROFILE_VERSION = "v1"
MODEL_VERSION = "advanced_v2"
SUPPORTED_SIGNALS = {
    "price_vs_comp",
    "size_vs_comp",
    "time_on_market",
    "feature_value",
    "confidence",
    "roi_proxy",
}


class RankingListingNotInRun(LookupError):
    """Raised when listing_id was not returned in the run's result window."""


class RankingRunNotFound(LookupError):
    """Raised when no persisted ranking run matches run_id."""


class RankingListingRowMissing(LookupError):
    """Raised when the listing row was deleted after the run was stored."""


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


@dataclass
class _ScoredRow:
    listing: Listing
    score: float
    confidence: float
    deal_reason: str
    explanation: dict[str, Any]


def build_ranking_result_item(
    listing: Listing,
    *,
    score: float,
    confidence: float,
    deal_reason: str,
    run_id: str,
) -> RankingResultItem:
    """Shared shape for ranking query responses and persisted run exports."""
    return RankingResultItem(
        listing_id=listing.id,
        score=score,
        deal_reason=deal_reason,
        confidence=confidence,
        summary={
            "price": listing.price,
            "city": listing.city,
            "suburb": listing.suburb,
            "property_type": listing.property_type,
        },
        detail_ref=f"{run_id}:listing-{listing.id}",
        listing_url=listing.listing_url,
        bedrooms=listing.bedrooms,
        bathrooms=listing.bathrooms,
        province=listing.province,
        source_site=listing.source_site,
    )


def _freshness_iso(db: Session, job_ids: list[int]) -> tuple[str | None, str | None]:
    jobs: list[IngestionJob] = []
    for jid in job_ids:
        job = db.get(IngestionJob, jid)
        if job is not None:
            jobs.append(job)
    ingested_times = [j.finished_at for j in jobs if j.finished_at]
    last_ingested = max(ingested_times) if ingested_times else None
    last_scored = db.scalar(
        select(func.max(ScoreResult.created_at)).where(ScoreResult.job_id.in_(job_ids))
    )

    def _iso(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        from datetime import UTC

        aware = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
        return aware.isoformat().replace("+00:00", "Z")

    return _iso(last_ingested), _iso(last_scored)


def _persist_ranking_run_with_listings(
    db: Session,
    *,
    run_id: str,
    query_fingerprint: str,
    request_payload: dict[str, Any],
    profile: ProfileDetailResponse,
    records_considered: int,
    result_count: int,
    scored_rows: list[_ScoredRow],
) -> RankingRun:
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

    run = RankingRun(
        run_id=run_id,
        query_fingerprint=query_fingerprint,
        strategy_preset=request_payload["strategy"]["preset"],
        resolved_profile_id=profile.profile_id,
        profile_row_id=backup.id,
        request_payload=request_payload,
        result_window=request_payload["result_window"],
        records_considered=records_considered,
        result_count=result_count,
    )
    db.add(run)
    db.flush()

    for ordinal, row in enumerate(scored_rows):
        db.add(
            RankingRunListing(
                ranking_run_id=run.id,
                listing_id=row.listing.id,
                ordinal=ordinal,
                score=row.score,
                confidence=row.confidence,
                deal_reason=row.deal_reason,
                explanation_snapshot=row.explanation,
            )
        )
    db.commit()
    db.refresh(run)
    return run


def run_ranking_query(
    request: RankingQueryRequest, db: Session | None = None
) -> RankingQueryResponse:
    if db is None:
        raise ValueError("run_ranking_query requires db=Session for Phase B ranking execution.")

    request_payload = request.model_dump(mode="json")
    query_fingerprint = _stable_json_hash(request_payload)
    run_id = f"run-{uuid4().hex[:12]}"

    profile = resolve_profile(request.strategy.preset, request.strategy.weight_overrides)

    job_ids = resolve_dataset_sources_to_job_ids(db, request.dataset_sources)
    merged = merge_listings_for_jobs(db, job_ids)
    if not merged:
        raise ValueError("No listings found for the selected dataset sources.")

    filtered = apply_ranking_filters(merged, request.filters)
    records_considered = len(filtered)

    scored_rows: list[_ScoredRow] = []
    for listing in filtered:
        score, confidence, deal_reason, explanation = score_listing_with_strategy_weights(
            listing,
            filtered,
            weights=profile.default_weights,
        )
        scored_rows.append(
            _ScoredRow(
                listing=listing,
                score=score,
                confidence=confidence,
                deal_reason=deal_reason,
                explanation=explanation,
            )
        )

    scored_rows.sort(key=lambda r: (-r.score, r.listing.id))

    if request.result_window.top_n is not None:
        windowed = scored_rows[: request.result_window.top_n]
    else:
        page = request.result_window.page or 1
        page_size = request.result_window.page_size or 20
        start = (page - 1) * page_size
        windowed = scored_rows[start : start + page_size]

    results: list[RankingResultItem] = []
    for row in windowed:
        results.append(
            build_ranking_result_item(
                row.listing,
                score=row.score,
                confidence=row.confidence,
                deal_reason=row.deal_reason,
                run_id=run_id,
            )
        )

    last_ingested_at, last_scored_at = _freshness_iso(db, job_ids)
    dataset_context = DatasetContext(
        selected_sources=request.dataset_sources,
        records_considered=records_considered,
        last_ingested_at=last_ingested_at,
        last_scored_at=last_scored_at,
        model_version=MODEL_VERSION,
        profile_version=profile.profile_version,
    )

    pagination: PaginationEnvelope | None = None
    top_n: TopNEnvelope | None = None
    if request.result_window.top_n is not None:
        top_n_requested = request.result_window.top_n
        top_n = TopNEnvelope(
            mode="top_n",
            top_n_requested=top_n_requested,
            top_n_returned=len(results),
        )
    else:
        page = request.result_window.page or 1
        page_size = request.result_window.page_size or 20
        pagination = PaginationEnvelope(
            mode="pagination",
            page=page,
            page_size=page_size,
            total_count=len(scored_rows),
        )

    run = _persist_ranking_run_with_listings(
        db,
        run_id=run_id,
        query_fingerprint=query_fingerprint,
        request_payload=request_payload,
        profile=profile,
        records_considered=records_considered,
        result_count=len(results),
        scored_rows=windowed,
    )
    resolved_profile = ResolvedProfile(
        profile_id=profile.profile_id,
        profile_row_id=run.profile_row_id,
        profile_version=profile.profile_version,
        resolved_weights=profile.default_weights,
        enabled_signals=profile.enabled_signals,
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


def _explanation_to_diagnostics(
    explanation: dict[str, Any], *, detail_ref: str, profile_id: str
) -> dict[str, Any]:
    signals_out: list[dict[str, Any]] = []
    for row in explanation.get("signals", []):
        signals_out.append(
            {
                "name": row["name"],
                "raw": row["raw_value"],
                "normalized": row["normalized_score"],
                "weighted": row["weighted_contribution"],
            }
        )
    return {
        "signals": signals_out,
        "comps_context": explanation.get("comps_context"),
        "roi_assumptions": explanation.get("roi_assumptions"),
        "risk_flags": explanation.get("risk_flags", []),
        "detail_ref": detail_ref,
        "profile_id": profile_id,
        "summary": explanation.get("summary"),
        "missing_fields": explanation.get("missing_fields", []),
    }


def get_listing_detail(run_id: str, listing_id: int, db: Session) -> ListingDetailResponse:
    run = db.scalar(select(RankingRun).where(RankingRun.run_id == run_id))
    if run is None:
        raise RankingRunNotFound(f"No ranking run found for run_id={run_id!r}.")

    row = db.scalar(
        select(RankingRunListing).where(
            RankingRunListing.ranking_run_id == run.id,
            RankingRunListing.listing_id == listing_id,
        )
    )
    if row is None:
        raise RankingListingNotInRun(f"Listing {listing_id} is not part of ranking run {run_id!r}.")

    listing = db.get(Listing, listing_id)
    if listing is None:
        raise RankingListingRowMissing(f"Listing id {listing_id} no longer exists.")

    detail_ref = f"{run_id}:listing-{listing_id}"
    diagnostics = _explanation_to_diagnostics(
        row.explanation_snapshot,
        detail_ref=detail_ref,
        profile_id=run.resolved_profile_id,
    )
    listing_core: dict[str, Any] = {"run_id": run_id, **listing_columns_public_dict(listing)}
    return ListingDetailResponse(
        listing_core=listing_core,
        score_summary={
            "score": row.score,
            "deal_reason": row.deal_reason,
            "model_version": MODEL_VERSION,
            "profile_version": PLACEHOLDER_PROFILE_VERSION,
            "profile_id": run.resolved_profile_id,
            "confidence": row.confidence,
        },
        diagnostics=diagnostics,
    )
