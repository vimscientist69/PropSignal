from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import correlation, median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.score_result import ScoreResult
from app.services.dataset_validation import run_dataset_validation
from app.services.scoring import _clamp, _load_scoring_config


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _compute_jaccard(left_ids: list[str], right_ids: list[str]) -> float:
    left_set = set(left_ids)
    right_set = set(right_ids)
    union_size = len(left_set | right_set)
    if union_size == 0:
        return 1.0
    return round(len(left_set & right_set) / union_size, 4)


def _spearman_rank_correlation(current_ids: list[str], reference_ids: list[str]) -> float:
    current_rank = {listing_id: idx + 1 for idx, listing_id in enumerate(current_ids)}
    reference_rank = {listing_id: idx + 1 for idx, listing_id in enumerate(reference_ids)}
    common_ids = sorted(set(current_rank) & set(reference_rank))
    if len(common_ids) < 2:
        return 0.0

    current_values = [float(current_rank[listing_id]) for listing_id in common_ids]
    reference_values = [float(reference_rank[listing_id]) for listing_id in common_ids]
    return round(float(correlation(current_values, reference_values)), 4)


def _sorted_scores(db: Session, job_id: int) -> list[ScoreResult]:
    return db.scalars(
        select(ScoreResult)
        .where(ScoreResult.job_id == job_id)
        .order_by(ScoreResult.score.desc(), ScoreResult.listing_id.asc())
    ).all()


def _ranking_identity_map(db: Session, job_id: int) -> dict[int, str]:
    listings = db.scalars(select(Listing).where(Listing.job_id == job_id)).all()
    identities: dict[int, str] = {}
    for listing in listings:
        external_listing_id = listing.listing_id
        identities[listing.id] = (
            external_listing_id
            if external_listing_id not in (None, "")
            else f"internal-{listing.id}"
        )
    return identities


def _dominance_ratio(score_row: ScoreResult) -> float:
    if not score_row.explanation:
        return 1.0
    signals = score_row.explanation.get("signals")
    if not isinstance(signals, list) or not signals:
        return 1.0

    contributions: list[float] = []
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        contributions.append(abs(float(signal.get("weighted_contribution", 0.0))))

    if not contributions:
        return 1.0
    total = sum(contributions)
    return round(_safe_divide(max(contributions), total), 4)


def _score_math_consistent(score_row: ScoreResult) -> bool:
    if not score_row.explanation:
        return False

    explanation = score_row.explanation
    signals = explanation.get("signals")
    score_math = explanation.get("score_math")
    if not isinstance(signals, list) or not isinstance(score_math, dict):
        return False

    weighted_sum = 0.0
    for signal in signals:
        if not isinstance(signal, dict):
            return False
        weighted_sum += float(signal.get("weighted_contribution", 0.0))

    expected_weighted_sum = float(score_math.get("weighted_sum_0_to_1", 0.0))
    expected_final_score = float(score_math.get("final_score_0_to_100", -1.0))
    return round(weighted_sum, 6) == round(expected_weighted_sum, 6) and round(
        score_row.score, 2
    ) == round(expected_final_score, 2)


def _extract_signal_vectors(score_row: ScoreResult) -> dict[str, tuple[float, float]]:
    explanation = score_row.explanation or {}
    signals = explanation.get("signals")
    if not isinstance(signals, list):
        return {}

    vectors: dict[str, tuple[float, float]] = {}
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        name = str(signal.get("name", ""))
        if not name:
            continue
        vectors[name] = (
            float(signal.get("normalized_score", 0.0)),
            float(signal.get("weight", 0.0)),
        )
    return vectors


def _perturbed_score(
    vectors: dict[str, tuple[float, float]],
    target_signal: str,
    delta: float,
) -> float:
    if not vectors:
        return 0.0

    perturbed_weights: dict[str, float] = {}
    for signal_name, (_normalized_score, weight) in vectors.items():
        if signal_name == target_signal:
            perturbed_weights[signal_name] = max(0.0, weight * (1.0 + delta))
        else:
            perturbed_weights[signal_name] = max(0.0, weight)

    weight_total = sum(perturbed_weights.values())
    if weight_total <= 0:
        return 0.0

    weighted_sum = 0.0
    for signal_name, (normalized_score, _weight) in vectors.items():
        normalized_weight = _safe_divide(perturbed_weights[signal_name], weight_total)
        weighted_sum += normalized_score * normalized_weight
    return round(_clamp(weighted_sum), 6)


def _compute_perturbation_overlap(
    rows: list[ScoreResult],
    top_n: int,
    deltas: list[float],
) -> tuple[float, list[dict[str, Any]]]:
    if not rows:
        return 0.0, []

    baseline_top_ids = [row.listing_id for row in rows[:top_n]]
    experiments: list[dict[str, Any]] = []
    overlaps: list[float] = []

    row_vectors: list[tuple[int, dict[str, tuple[float, float]]]] = []
    signal_names: set[str] = set()
    for row in rows:
        vectors = _extract_signal_vectors(row)
        if not vectors:
            continue
        row_vectors.append((row.listing_id, vectors))
        signal_names.update(vectors.keys())
    if not signal_names:
        return 0.0, []

    for signal_name in sorted(signal_names):
        for delta in deltas:
            perturbed_rows: list[tuple[int, float]] = []
            for listing_id, vectors in row_vectors:
                perturbed_rows.append(
                    (
                        listing_id,
                        _perturbed_score(vectors, target_signal=signal_name, delta=delta),
                    )
                )

            perturbed_rows.sort(key=lambda entry: (-entry[1], entry[0]))
            perturbed_top_ids = [listing_id for listing_id, _score in perturbed_rows[:top_n]]
            overlap = _compute_jaccard(baseline_top_ids, perturbed_top_ids)
            overlaps.append(overlap)
            experiments.append(
                {
                    "signal": signal_name,
                    "delta": delta,
                    "top_n_jaccard": overlap,
                }
            )

    if not overlaps:
        return 0.0, experiments
    return round(min(overlaps), 4), experiments


def _segment_bounds(total_count: int, start_pct: float, end_pct: float) -> tuple[int, int]:
    if total_count <= 0:
        return (0, 0)
    start = int(total_count * _clamp(start_pct))
    end = int(total_count * _clamp(end_pct))
    start = max(0, min(start, total_count))
    end = max(0, min(end, total_count))
    if end <= start:
        end = min(total_count, start + 1)
    return (start, end)


def _segment_identities(
    rows: list[ScoreResult],
    identity_map: dict[int, str],
    start_idx: int,
    end_idx: int,
) -> list[str]:
    segment_rows = rows[start_idx:end_idx]
    return [identity_map.get(row.listing_id, f"internal-{row.listing_id}") for row in segment_rows]


def _global_rank_map(identities: list[str]) -> dict[str, int]:
    return {identity: idx + 1 for idx, identity in enumerate(identities)}


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * _clamp(pct)))
    return float(ordered[idx])


def _rank_displacement_metrics(
    current_ids: list[str],
    reference_ids: list[str],
    current_global_rank: dict[str, int],
    reference_global_rank: dict[str, int],
) -> dict[str, float]:
    shared_ids = sorted(set(current_ids) & set(reference_ids))
    if not shared_ids:
        return {
            "intersection_count": 0.0,
            "median_abs_rank_shift": 0.0,
            "p90_rank_shift": 0.0,
            "median_abs_rank_shift_pct": 0.0,
            "p90_rank_shift_pct": 0.0,
        }

    shifts = [
        float(abs(current_global_rank[listing_id] - reference_global_rank[listing_id]))
        for listing_id in shared_ids
    ]
    rank_span = max(len(current_global_rank), len(reference_global_rank)) - 1
    rank_span = max(rank_span, 1)
    shift_pcts = [shift / rank_span for shift in shifts]
    return {
        "intersection_count": float(len(shared_ids)),
        "median_abs_rank_shift": round(float(median(shifts)), 4),
        "p90_rank_shift": round(_percentile(shifts, 0.90), 4),
        "median_abs_rank_shift_pct": round(float(median(shift_pcts)), 6),
        "p90_rank_shift_pct": round(_percentile(shift_pcts, 0.90), 6),
    }


def _evaluate_segment_stability(
    *,
    segment_name: str,
    current_ids: list[str],
    reference_ids: list[str],
    current_global_rank: dict[str, int],
    reference_global_rank: dict[str, int],
    thresholds: dict[str, Any],
    severity: str,
) -> dict[str, Any]:
    jaccard_overlap = _compute_jaccard(current_ids, reference_ids)
    rank_correlation = _spearman_rank_correlation(current_ids, reference_ids)
    displacement = _rank_displacement_metrics(
        current_ids,
        reference_ids,
        current_global_rank,
        reference_global_rank,
    )
    intersection_count = int(displacement["intersection_count"])

    failed_checks: list[str] = []
    if severity == "fail":
        jaccard_min = thresholds.get("jaccard_min")
        if jaccard_min is not None and jaccard_overlap < float(jaccard_min):
            failed_checks.append(f"jaccard_below_min:{jaccard_overlap}<{jaccard_min}")
        rank_corr_min = thresholds.get("rank_correlation_min")
        if rank_corr_min is not None and rank_correlation < float(rank_corr_min):
            failed_checks.append(f"rank_corr_below_min:{rank_correlation}<{rank_corr_min}")
        median_pct_max = thresholds.get("median_abs_rank_shift_pct_max")
        if median_pct_max is not None and displacement["median_abs_rank_shift_pct"] > float(
            median_pct_max
        ):
            failed_checks.append(
                "median_abs_rank_shift_pct_above_max:"
                f"{displacement['median_abs_rank_shift_pct']}>{median_pct_max}"
            )
        p90_pct_max = thresholds.get("p90_rank_shift_pct_max")
        if p90_pct_max is not None and displacement["p90_rank_shift_pct"] > float(p90_pct_max):
            failed_checks.append(
                f"p90_rank_shift_pct_above_max:{displacement['p90_rank_shift_pct']}>{p90_pct_max}"
            )
    else:
        jaccard_warn_min = thresholds.get("jaccard_warn_min")
        if jaccard_warn_min is not None and jaccard_overlap < float(jaccard_warn_min):
            failed_checks.append(f"jaccard_below_warn_min:{jaccard_overlap}<{jaccard_warn_min}")
        rank_corr_warn_min = thresholds.get("rank_correlation_warn_min")
        if rank_corr_warn_min is not None and rank_correlation < float(rank_corr_warn_min):
            failed_checks.append(
                f"rank_corr_below_warn_min:{rank_correlation}<{rank_corr_warn_min}"
            )
        median_pct_warn_max = thresholds.get("median_abs_rank_shift_pct_warn_max")
        if median_pct_warn_max is not None and displacement["median_abs_rank_shift_pct"] > float(
            median_pct_warn_max
        ):
            failed_checks.append(
                "median_abs_rank_shift_pct_above_warn_max:"
                f"{displacement['median_abs_rank_shift_pct']}>{median_pct_warn_max}"
            )
        p90_pct_warn_max = thresholds.get("p90_rank_shift_pct_warn_max")
        if p90_pct_warn_max is not None and displacement["p90_rank_shift_pct"] > float(
            p90_pct_warn_max
        ):
            failed_checks.append(
                "p90_rank_shift_pct_above_warn_max:"
                f"{displacement['p90_rank_shift_pct']}>{p90_pct_warn_max}"
            )

    status = "pass" if not failed_checks else severity
    return {
        "segment_name": segment_name,
        "status": status,
        "metrics": {
            "sample_size_current": len(current_ids),
            "sample_size_reference": len(reference_ids),
            "intersection_count": intersection_count,
            "jaccard_overlap": jaccard_overlap,
            "rank_correlation": rank_correlation,
            "median_abs_rank_shift": displacement["median_abs_rank_shift"],
            "p90_rank_shift": displacement["p90_rank_shift"],
            "median_abs_rank_shift_pct": displacement["median_abs_rank_shift_pct"],
            "p90_rank_shift_pct": displacement["p90_rank_shift_pct"],
        },
        "thresholds": thresholds,
        "violation_details": {"failed_checks": failed_checks},
    }


def run_scoring_evaluation(
    db: Session,
    job_id: int,
    reference_job_id: int | None = None,
    top_n: int = 20,
) -> dict[str, Any]:
    config = _load_scoring_config()
    thresholds = config.get("evaluation_thresholds", {})
    data_thresholds = thresholds.get("data_quality", {})
    sanity_thresholds = thresholds.get("scoring_sanity", {})
    stability_thresholds = thresholds.get("stability", {})
    decision_thresholds = thresholds.get("decision", {})

    current_rows = _sorted_scores(db, job_id)
    if not current_rows:
        raise ValueError(f"No scored listings found for job: {job_id}")

    model_version = current_rows[0].model_version
    current_identity_map = _ranking_identity_map(db, job_id)
    top_n_effective = int(top_n) if top_n > 0 else 20
    sampled_rows = current_rows[:top_n_effective]

    validation = run_dataset_validation(db, job_id)
    valid_rate_min = float(data_thresholds.get("valid_rate_min", 0.85))
    duplicate_rate_max = float(data_thresholds.get("duplicate_rate_max", 0.05))
    price_null_rate_max = float(data_thresholds.get("price_null_rate_max", 0.10))

    data_quality_pass = (
        validation.valid_rate >= valid_rate_min
        and validation.duplicate_rate <= duplicate_rate_max
        and validation.price_null_rate <= price_null_rate_max
    )
    data_quality_failures: list[str] = []
    if validation.valid_rate < valid_rate_min:
        data_quality_failures.append(
            f"valid_rate_below_min: actual={validation.valid_rate}, required>={valid_rate_min}"
        )
    if validation.duplicate_rate > duplicate_rate_max:
        data_quality_failures.append(
            "duplicate_rate_above_max: "
            f"actual={validation.duplicate_rate}, required<={duplicate_rate_max}"
        )
    if validation.price_null_rate > price_null_rate_max:
        data_quality_failures.append(
            "price_null_rate_above_max: "
            f"actual={validation.price_null_rate}, required<={price_null_rate_max}"
        )
    data_quality_gate = {
        "status": "pass" if data_quality_pass else "fail",
        "failure_reasons": data_quality_failures,
        "violation_details": {
            "record_level_ids_available": False,
            "inspection_hint": (
                "Data-quality checks are aggregate metrics from dataset validation; "
                "use the dataset validation report for deeper raw-row diagnostics."
            ),
        },
        "metrics": {
            "valid_rate": validation.valid_rate,
            "duplicate_rate": validation.duplicate_rate,
            "price_null_rate": validation.price_null_rate,
        },
        "thresholds": {
            "valid_rate_min": valid_rate_min,
            "duplicate_rate_max": duplicate_rate_max,
            "price_null_rate_max": price_null_rate_max,
        },
    }

    score_min = float(sanity_thresholds.get("score_min", 0.0))
    score_max = float(sanity_thresholds.get("score_max", 100.0))
    dominance_cap = float(sanity_thresholds.get("signal_dominance_cap", 0.70))
    high_score_cutoff = float(sanity_thresholds.get("high_score_cutoff", 80.0))

    out_of_range_rows = [
        {
            "listing_db_id": row.listing_id,
            "listing_identity": current_identity_map.get(
                row.listing_id, f"internal-{row.listing_id}"
            ),
            "score": row.score,
        }
        for row in current_rows
        if row.score < score_min or row.score > score_max
    ]
    listing_lookup = {
        listing.id: listing
        for listing in db.scalars(select(Listing).where(Listing.job_id == job_id)).all()
    }
    impossible_top_ranked_rows: list[dict[str, Any]] = []
    for row in sampled_rows:
        listing = listing_lookup.get(row.listing_id)
        if listing and listing.price <= 0 and row.score >= high_score_cutoff:
            impossible_top_ranked_rows.append(
                {
                    "listing_db_id": row.listing_id,
                    "listing_identity": current_identity_map.get(
                        row.listing_id, f"internal-{row.listing_id}"
                    ),
                    "score": row.score,
                    "price": listing.price,
                }
            )

    dominance_violation_rows = []
    for row in sampled_rows:
        dominance_ratio = _dominance_ratio(row)
        if dominance_ratio > dominance_cap:
            dominance_violation_rows.append(
                {
                    "listing_db_id": row.listing_id,
                    "listing_identity": current_identity_map.get(
                        row.listing_id, f"internal-{row.listing_id}"
                    ),
                    "dominance_ratio": dominance_ratio,
                }
            )
    scoring_sanity_pass = (
        len(out_of_range_rows) == 0
        and len(impossible_top_ranked_rows) == 0
        and len(dominance_violation_rows) == 0
    )
    scoring_sanity_gate = {
        "status": "pass" if scoring_sanity_pass else "fail",
        "violation_details": {
            "out_of_range_rows": out_of_range_rows,
            "impossible_top_ranked_rows": impossible_top_ranked_rows,
            "dominance_violation_rows": dominance_violation_rows,
        },
        "metrics": {
            "out_of_range_count": len(out_of_range_rows),
            "impossible_top_ranked_count": len(impossible_top_ranked_rows),
            "dominance_violations": len(dominance_violation_rows),
        },
        "thresholds": {
            "score_min": score_min,
            "score_max": score_max,
            "signal_dominance_cap": dominance_cap,
            "high_score_cutoff": high_score_cutoff,
        },
    }

    missing_explanation_rows = [
        {
            "listing_db_id": row.listing_id,
            "listing_identity": current_identity_map.get(
                row.listing_id, f"internal-{row.listing_id}"
            ),
        }
        for row in sampled_rows
        if not row.explanation
    ]
    score_math_mismatch_rows = [
        {
            "listing_db_id": row.listing_id,
            "listing_identity": current_identity_map.get(
                row.listing_id, f"internal-{row.listing_id}"
            ),
        }
        for row in sampled_rows
        if not _score_math_consistent(row)
    ]
    explainability_pass = len(missing_explanation_rows) == 0 and len(score_math_mismatch_rows) == 0
    explainability_gate = {
        "status": "pass" if explainability_pass else "fail",
        "violation_details": {
            "missing_explanation_rows": missing_explanation_rows,
            "score_math_mismatch_rows": score_math_mismatch_rows,
        },
        "metrics": {
            "missing_explanations_top_n": len(missing_explanation_rows),
            "score_math_mismatches_top_n": len(score_math_mismatch_rows),
        },
        "thresholds": {
            "required_top_n": top_n_effective,
        },
    }

    stability_gate: dict[str, Any]
    stability_warning_keys: list[str] = []
    if reference_job_id is None:
        stability_gate = {
            "status": "warn",
            "reason": "reference_job_id_not_provided",
            "metrics": {},
            "thresholds": {},
        }
    else:
        reference_rows = _sorted_scores(db, reference_job_id)
        reference_identity_map = _ranking_identity_map(db, reference_job_id)
        current_global_ids = _segment_identities(
            current_rows, current_identity_map, 0, len(current_rows)
        )
        reference_global_ids = _segment_identities(
            reference_rows, reference_identity_map, 0, len(reference_rows)
        )
        current_global_rank = _global_rank_map(current_global_ids)
        reference_global_rank = _global_rank_map(reference_global_ids)

        segments_cfg = stability_thresholds.get("segments", {})
        top_cfg = dict(segments_cfg.get("top_band", {}))
        middle_cfg = dict(segments_cfg.get("middle_band", {}))
        bottom_cfg = dict(segments_cfg.get("bottom_band", {}))
        full_dataset_cfg = dict(stability_thresholds.get("full_dataset", {}))

        top_n_cfg = int(top_cfg.get("top_n", top_n_effective))
        top_count = top_n_effective if top_n > 0 else top_n_cfg
        top_current_ids = _segment_identities(current_rows, current_identity_map, 0, top_count)
        top_reference_ids = _segment_identities(
            reference_rows, reference_identity_map, 0, top_count
        )
        top_band = _evaluate_segment_stability(
            segment_name="top_band",
            current_ids=top_current_ids,
            reference_ids=top_reference_ids,
            current_global_rank=current_global_rank,
            reference_global_rank=reference_global_rank,
            thresholds=top_cfg,
            severity="fail",
        )

        perturbation_deltas = [-0.10, -0.05, 0.05, 0.10]
        perturbation_overlap_min, perturbation_details = _compute_perturbation_overlap(
            current_rows, top_n=top_count, deltas=perturbation_deltas
        )
        top_band["metrics"]["perturbation_overlap_min"] = perturbation_overlap_min
        top_band["metrics"]["perturbation_checks"] = perturbation_details
        perturbation_threshold = float(top_cfg.get("perturbation_overlap_min", 0.60))
        top_band["thresholds"]["perturbation_overlap_min"] = perturbation_threshold
        if perturbation_overlap_min < perturbation_threshold:
            top_band["status"] = "fail"
            top_band["violation_details"]["failed_checks"].append(
                f"perturbation_overlap_below_min:{perturbation_overlap_min}<{perturbation_threshold}"
            )

        middle_start_pct = float(middle_cfg.get("start_pct", 0.45))
        middle_end_pct = float(middle_cfg.get("end_pct", 0.60))
        middle_current_bounds = _segment_bounds(len(current_rows), middle_start_pct, middle_end_pct)
        middle_reference_bounds = _segment_bounds(
            len(reference_rows), middle_start_pct, middle_end_pct
        )
        middle_band = _evaluate_segment_stability(
            segment_name="middle_band",
            current_ids=_segment_identities(
                current_rows,
                current_identity_map,
                middle_current_bounds[0],
                middle_current_bounds[1],
            ),
            reference_ids=_segment_identities(
                reference_rows,
                reference_identity_map,
                middle_reference_bounds[0],
                middle_reference_bounds[1],
            ),
            current_global_rank=current_global_rank,
            reference_global_rank=reference_global_rank,
            thresholds=middle_cfg,
            severity="warn",
        )

        bottom_start_pct = float(bottom_cfg.get("start_pct", 0.85))
        bottom_end_pct = float(bottom_cfg.get("end_pct", 1.00))
        bottom_current_bounds = _segment_bounds(len(current_rows), bottom_start_pct, bottom_end_pct)
        bottom_reference_bounds = _segment_bounds(
            len(reference_rows), bottom_start_pct, bottom_end_pct
        )
        bottom_band = _evaluate_segment_stability(
            segment_name="bottom_band",
            current_ids=_segment_identities(
                current_rows,
                current_identity_map,
                bottom_current_bounds[0],
                bottom_current_bounds[1],
            ),
            reference_ids=_segment_identities(
                reference_rows,
                reference_identity_map,
                bottom_reference_bounds[0],
                bottom_reference_bounds[1],
            ),
            current_global_rank=current_global_rank,
            reference_global_rank=reference_global_rank,
            thresholds=bottom_cfg,
            severity="warn",
        )

        full_displacement = _rank_displacement_metrics(
            current_global_ids,
            reference_global_ids,
            current_global_rank,
            reference_global_rank,
        )
        full_warn_checks: list[str] = []
        full_median_pct_warn_max = float(
            full_dataset_cfg.get("median_abs_rank_shift_pct_warn_max", 0.35)
        )
        full_p90_pct_warn_max = float(full_dataset_cfg.get("p90_rank_shift_pct_warn_max", 0.80))
        if full_displacement["median_abs_rank_shift_pct"] > full_median_pct_warn_max:
            full_warn_checks.append(
                "median_abs_rank_shift_pct_above_warn_max:"
                f"{full_displacement['median_abs_rank_shift_pct']}>{full_median_pct_warn_max}"
            )
        if full_displacement["p90_rank_shift_pct"] > full_p90_pct_warn_max:
            full_warn_checks.append(
                "p90_rank_shift_pct_above_warn_max:"
                f"{full_displacement['p90_rank_shift_pct']}>{full_p90_pct_warn_max}"
            )
        full_dataset_status = "warn" if full_warn_checks else "pass"
        full_dataset_metrics = {
            "intersection_count": int(full_displacement["intersection_count"]),
            "median_abs_rank_shift": full_displacement["median_abs_rank_shift"],
            "p90_rank_shift": full_displacement["p90_rank_shift"],
            "median_abs_rank_shift_pct": full_displacement["median_abs_rank_shift_pct"],
            "p90_rank_shift_pct": full_displacement["p90_rank_shift_pct"],
            "thresholds": {
                "median_abs_rank_shift_pct_warn_max": full_median_pct_warn_max,
                "p90_rank_shift_pct_warn_max": full_p90_pct_warn_max,
            },
            "status": full_dataset_status,
            "violation_details": {"failed_checks": full_warn_checks},
        }

        if middle_band["status"] == "warn":
            stability_warning_keys.append("stability_middle_band")
        if bottom_band["status"] == "warn":
            stability_warning_keys.append("stability_bottom_band")
        if full_dataset_status == "warn":
            stability_warning_keys.append("stability_full_dataset")

        has_top_fail = top_band["status"] == "fail"
        has_warnings = bool(stability_warning_keys)
        stability_gate = {
            "status": "fail" if has_top_fail else ("warn" if has_warnings else "pass"),
            "metrics": {
                "segments": {
                    "top_band": top_band,
                    "middle_band": middle_band,
                    "bottom_band": bottom_band,
                },
                "full_dataset": full_dataset_metrics,
            },
            "thresholds": {
                "segments": segments_cfg,
                "full_dataset": full_dataset_cfg,
            },
        }

    minimum_sample_for_promote = int(decision_thresholds.get("minimum_sample_for_promote", 100))
    warning_gate_keys: list[str] = []
    failed_gate_keys: list[str] = []
    for gate_key, gate_payload in {
        "data_quality": data_quality_gate,
        "scoring_sanity": scoring_sanity_gate,
        "stability": stability_gate,
        "explainability": explainability_gate,
    }.items():
        if gate_payload["status"] == "fail":
            failed_gate_keys.append(gate_key)
        elif gate_payload["status"] == "warn":
            warning_gate_keys.append(gate_key)
    warning_gate_keys.extend(stability_warning_keys)

    decision: str
    decision_reasons: list[str] = []
    if failed_gate_keys:
        decision = "revert"
        decision_reasons.append("One or more critical gates failed.")
    elif len(current_rows) < minimum_sample_for_promote:
        decision = "experimental"
        warning_gate_keys.append("sample_size")
        decision_reasons.append("Sample size below promote threshold.")
    elif warning_gate_keys:
        decision = "experimental"
        decision_reasons.append("No critical failures, but warning gates are present.")
    else:
        decision = "promote"
        decision_reasons.append("All required gates passed.")

    recommended_next_actions: list[str] = []
    if decision == "revert":
        recommended_next_actions.append("Rollback scoring profile changes and review failed gates.")
    elif decision == "experimental":
        recommended_next_actions.append("Collect more data and rerun evaluation before promotion.")
    else:
        recommended_next_actions.append("Promote scoring profile and monitor post-release metrics.")

    evaluation_time_utc = datetime.now(UTC)
    timestamp_compact = evaluation_time_utc.strftime("%Y%m%d%H%M%S")
    timestamp_readable = evaluation_time_utc.strftime("%Y-%m-%d_%H-%M-%SZ")
    run_id = f"job-{job_id}-ref-{reference_job_id or 'none'}-{timestamp_compact}"
    output_dir = Path("output") / "evaluations" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"scoring_evaluation_{timestamp_readable}.json"

    report = {
        "run_id": run_id,
        "job_id": job_id,
        "reference_job_id": reference_job_id,
        "model_version": model_version,
        "timestamp_utc": evaluation_time_utc.isoformat(),
        "sample_size": len(current_rows),
        "top_n": top_n_effective,
        "gates": {
            "data_quality": data_quality_gate,
            "scoring_sanity": scoring_sanity_gate,
            "stability": stability_gate,
            "explainability": explainability_gate,
        },
        "decision": decision,
        "decision_reasons": decision_reasons,
        "failed_gates": failed_gate_keys,
        "warning_gates": sorted(set(warning_gate_keys)),
        "recommended_next_actions": recommended_next_actions,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["report_path"] = str(report_path)
    return report
