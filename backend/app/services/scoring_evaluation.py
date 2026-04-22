from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import correlation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.score_result import ScoreResult
from app.services.dataset_validation import run_dataset_validation
from app.services.scoring import _clamp, _load_scoring_config


def _safe_divide(numerator: float, denominator: float) -> float:
    """Divide safely and return 0.0 on zero denominator.

    Why this exists:
    - Evaluation math uses ratios in multiple places.
    - A zero denominator should not crash a release-gate run.
    """
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _compute_jaccard(left_ids: list[str], right_ids: list[str]) -> float:
    """Measure set overlap using Jaccard similarity.

    Formula:
    - |intersection| / |union|

    Interpretation:
    - 1.0 means the sets are identical.
    - 0.0 means no overlap.
    - Used here to check whether top-N listings stayed mostly the same.
    """
    left_set = set(left_ids)
    right_set = set(right_ids)
    union_size = len(left_set | right_set)
    if union_size == 0:
        return 1.0
    return round(len(left_set & right_set) / union_size, 4)


def _spearman_rank_correlation(current_ids: list[str], reference_ids: list[str]) -> float:
    """Compare ordering consistency between two ranked lists.

    How it works:
    - Convert each list into rank positions.
    - Keep only items that appear in both lists.
    - Compute correlation on those rank positions.

    Interpretation:
    - +1.0: near-identical order
    - 0.0: weak relationship
    - -1.0: near-reversed order

    Why it matters:
    - Top-N overlap alone can look fine while overall ordering drifts heavily.
    """
    current_rank = {listing_id: idx + 1 for idx, listing_id in enumerate(current_ids)}
    reference_rank = {listing_id: idx + 1 for idx, listing_id in enumerate(reference_ids)}
    common_ids = sorted(set(current_rank) & set(reference_rank))
    if len(common_ids) < 2:
        return 0.0

    current_values = [float(current_rank[listing_id]) for listing_id in common_ids]
    reference_values = [float(reference_rank[listing_id]) for listing_id in common_ids]
    return round(float(correlation(current_values, reference_values)), 4)


def _sorted_scores(db: Session, job_id: int) -> list[ScoreResult]:
    """Fetch one job's score rows in deterministic rank order.

    Sort order:
    - Primary: score descending (higher scores rank first).
    - Secondary: listing_id ascending as a deterministic tie-breaker.

    Tie-breakers are important so repeated runs produce stable ordering for equal scores.
    """
    # listing_id is used only as a deterministic tie-breaker when scores are equal.
    return db.scalars(
        select(ScoreResult)
        .where(ScoreResult.job_id == job_id)
        .order_by(ScoreResult.score.desc(), ScoreResult.listing_id.asc())
    ).all()


def _ranking_identity_map(db: Session, job_id: int) -> dict[int, str]:
    """Map internal DB listing IDs to cross-run comparable IDs.

    Why this exists:
    - `score_results.listing_id` is an internal DB key and differs across jobs.
    - Stability comparisons should use a stable external identity.

    Strategy:
    - Prefer external `listing.listing_id`.
    - Fall back to `internal-<id>` when external ID is missing.
    """
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
    """Compute how much one signal dominates the explanation contributions.

    Formula:
    - max(abs(weighted_contribution)) / sum(abs(weighted_contribution))

    Interpretation:
    - Values near 1.0 indicate one signal is doing almost all the work.
    - High dominance can indicate brittle or unbalanced scoring.
    """
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
    """Validate that explanation math matches stored score values.

    Checks:
    - Re-sum `signals[].weighted_contribution` and compare to
      `score_math.weighted_sum_0_to_1`.
    - Compare row `score` to `score_math.final_score_0_to_100`.

    This protects against explainability drift where narrative payloads disagree
    with actual scoring outputs.
    """
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
    """Extract per-signal (normalized_score, weight) pairs from explanation payload.

    Output shape:
    - {signal_name: (normalized_score, weight)}

    This is the base structure used for perturbation sensitivity simulations.
    """
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
    """Recompute a simulated score after perturbing one signal weight.

    Process:
    - Increase/decrease one target weight by `delta` (e.g., +0.05 or -0.10).
    - Keep other weights unchanged.
    - Re-normalize all weights to sum to 1.
    - Recompute weighted score.

    Purpose:
    - Estimate sensitivity: does a small weight tweak cause large ranking movement?
    """
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
    """Run perturbation experiments and measure top-N stability.

    For each signal and each delta:
    - recompute perturbed scores
    - rerank listings
    - compare perturbed top-N vs baseline top-N using Jaccard

    Returns:
    - minimum top-N overlap across all experiments (worst-case stability)
    - detailed per-experiment metrics for audit/debugging
    """
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


# continue here
def run_scoring_evaluation(
    db: Session,
    job_id: int,
    reference_job_id: int | None = None,
    top_n: int = 20,
) -> dict[str, Any]:
    """Evaluate one scoring run and produce a release decision artifact.

    Gate families:
    - Data quality: valid/duplicate/null-rate thresholds.
    - Scoring sanity: score bounds, impossible top ranks, signal dominance.
    - Explainability: payload presence and math consistency.
    - Stability: top-N overlap, rank correlation, perturbation robustness.

    Decision logic:
    - `revert` if any critical gate fails.
    - `experimental` if sample is too small or warnings remain.
    - `promote` only when all required gates pass.

    Side effect:
    - Writes `output/evaluations/<run_id>/scoring_evaluation_<timestamp>.json`.
    """
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
    sampled_rows = current_rows[:top_n]
    current_identity_map = _ranking_identity_map(db, job_id)

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
            "required_top_n": top_n,
        },
    }

    stability_gate: dict[str, Any]
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
        reference_top_ids = [
            reference_identity_map.get(row.listing_id, f"internal-{row.listing_id}")
            for row in reference_rows[:top_n]
        ]
        current_top_ids = [
            current_identity_map.get(row.listing_id, f"internal-{row.listing_id}")
            for row in current_rows[:top_n]
        ]
        top_n_jaccard = _compute_jaccard(current_top_ids, reference_top_ids)
        rank_corr = _spearman_rank_correlation(
            [
                current_identity_map.get(row.listing_id, f"internal-{row.listing_id}")
                for row in current_rows
            ],
            [
                reference_identity_map.get(row.listing_id, f"internal-{row.listing_id}")
                for row in reference_rows
            ],
        )
        perturbation_deltas = [-0.10, -0.05, 0.05, 0.10]
        perturbation_overlap_min, perturbation_details = _compute_perturbation_overlap(
            current_rows, top_n=top_n, deltas=perturbation_deltas
        )

        top_n_jaccard_min = float(stability_thresholds.get("top20_jaccard_min", 0.70))
        rank_correlation_min = float(stability_thresholds.get("rank_correlation_min", 0.80))
        perturbation_overlap_min_threshold = float(
            stability_thresholds.get("perturbation_overlap_min", 0.60)
        )
        stability_pass = (
            top_n_jaccard >= top_n_jaccard_min
            and rank_corr >= rank_correlation_min
            and perturbation_overlap_min >= perturbation_overlap_min_threshold
        )
        stability_gate = {
            "status": "pass" if stability_pass else "fail",
            "metrics": {
                "top_n_jaccard": top_n_jaccard,
                "rank_correlation": rank_corr,
                "perturbation_overlap_min": perturbation_overlap_min,
                "perturbation_checks": perturbation_details,
            },
            "thresholds": {
                "top_n_jaccard_min": top_n_jaccard_min,
                "rank_correlation_min": rank_correlation_min,
                "perturbation_overlap_min": perturbation_overlap_min_threshold,
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

    # continue here
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
        "top_n": top_n,
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
