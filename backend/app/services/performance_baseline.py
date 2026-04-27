from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.services.dataset_validation import run_dataset_validation
from app.services.ingestion import ingest_propflux_file
from app.services.scoring import run_scoring_job
from app.services.scoring_evaluation import run_scoring_evaluation


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * max(0.0, min(1.0, pct))))
    return float(ordered[idx])


def _timed(callable_fn: Any, *args: Any, **kwargs: Any) -> tuple[Any, float]:
    start = perf_counter()
    result = callable_fn(*args, **kwargs)
    elapsed = perf_counter() - start
    return result, round(elapsed, 4)


def run_performance_baseline(
    db: Session,
    dataset_paths: list[str],
    *,
    top_n: int = 20,
    output_dir: str | None = None,
) -> dict[str, Any]:
    if not dataset_paths:
        raise ValueError("At least one dataset path is required.")

    run_time_utc = datetime.now(UTC)
    run_id = f"phase4-baseline-{run_time_utc.strftime('%Y%m%d%H%M%S')}"
    base_dir = Path(output_dir) if output_dir else Path("output") / "performance" / run_id
    base_dir.mkdir(parents=True, exist_ok=True)

    dataset_results: list[dict[str, Any]] = []
    ingest_durations: list[float] = []
    score_durations: list[float] = []
    validate_durations: list[float] = []
    evaluate_durations: list[float] = []

    for dataset_path in dataset_paths:
        result: dict[str, Any] = {
            "dataset_path": dataset_path,
            "job_id": None,
            "durations_s": {
                "ingest": 0.0,
                "score": 0.0,
                "validate_dataset": 0.0,
                "evaluate_scoring": 0.0,
            },
            "artifacts": {
                "validation_report_path": None,
                "evaluation_report_path": None,
            },
            "status": "error",
            "error": None,
        }
        try:
            ingestion_job, ingest_s = _timed(ingest_propflux_file, db, Path(dataset_path))
            result["job_id"] = ingestion_job.id
            result["durations_s"]["ingest"] = ingest_s
            ingest_durations.append(ingest_s)

            _scoring_job, score_s = _timed(run_scoring_job, db, ingestion_job.id)
            result["durations_s"]["score"] = score_s
            score_durations.append(score_s)

            validation_result, validate_s = _timed(run_dataset_validation, db, ingestion_job.id)
            result["durations_s"]["validate_dataset"] = validate_s
            result["artifacts"]["validation_report_path"] = str(
                Path(validation_result.report_path).resolve()
            )
            validate_durations.append(validate_s)

            evaluation_report, evaluate_s = _timed(
                run_scoring_evaluation,
                db,
                job_id=ingestion_job.id,
                reference_job_id=ingestion_job.id,
                top_n=top_n,
            )
            result["durations_s"]["evaluate_scoring"] = evaluate_s
            evaluation_report_path = evaluation_report.get("report_path")
            if evaluation_report_path is not None:
                result["artifacts"]["evaluation_report_path"] = str(
                    Path(evaluation_report_path).resolve()
                )
            evaluate_durations.append(evaluate_s)

            result["status"] = "pass"
        except Exception as exc:  # pragma: no cover - defensive path
            result["error"] = str(exc)
            result["status"] = "error"
        dataset_results.append(result)

    aggregate = {
        "ingest": {
            "p50_s": _percentile(ingest_durations, 0.50),
            "p95_s": _percentile(ingest_durations, 0.95),
        },
        "score": {
            "p50_s": _percentile(score_durations, 0.50),
            "p95_s": _percentile(score_durations, 0.95),
        },
        "validate_dataset": {
            "p50_s": _percentile(validate_durations, 0.50),
            "p95_s": _percentile(validate_durations, 0.95),
        },
        "evaluate_scoring": {
            "p50_s": _percentile(evaluate_durations, 0.50),
            "p95_s": _percentile(evaluate_durations, 0.95),
        },
    }

    slo_targets = {
        "scoring_run_10k_max_s": 600.0,
        "dataset_validation_10k_max_s": 300.0,
        "ranking_list_api_p95_ms": 800.0,
        "filtered_ranking_api_p95_ms": 1200.0,
        "listing_detail_api_p95_ms": 500.0,
    }
    slo_assessment: dict[str, list[str]] = {"met": [], "missed": [], "deferred": []}
    if aggregate["score"]["p95_s"] <= slo_targets["scoring_run_10k_max_s"]:
        slo_assessment["met"].append("scoring_run_10k_max_s")
    else:
        slo_assessment["missed"].append("scoring_run_10k_max_s")
    if aggregate["validate_dataset"]["p95_s"] <= slo_targets["dataset_validation_10k_max_s"]:
        slo_assessment["met"].append("dataset_validation_10k_max_s")
    else:
        slo_assessment["missed"].append("dataset_validation_10k_max_s")
    slo_assessment["deferred"].extend(
        ["ranking_list_api_p95_ms", "filtered_ranking_api_p95_ms", "listing_detail_api_p95_ms"]
    )

    metrics = {
        "run_id": run_id,
        "timestamp_utc": run_time_utc.isoformat(),
        "scope": "week2_phase4_minimal_baseline",
        "datasets": dataset_results,
        "aggregate": aggregate,
        "slo_targets": slo_targets,
        "slo_assessment": slo_assessment,
        "bottlenecks": [],
        "week3_week4_followups": [
            "Add API-level latency benchmark harness and capture p95.",
            "Add query/index optimization for ranking/filter paths.",
            "Add async orchestration and cache strategy where needed.",
        ],
    }

    metrics_path = base_dir / "baseline_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    summary_lines = [
        "# Phase 4 Baseline Summary",
        "",
        f"- Run ID: {run_id}",
        f"- Timestamp UTC: {run_time_utc.isoformat()}",
        f"- Dataset count: {len(dataset_results)}",
        "",
        "## Stage p50/p95 (seconds)",
        f"- ingest: p50={aggregate['ingest']['p50_s']}, p95={aggregate['ingest']['p95_s']}",
        f"- score: p50={aggregate['score']['p50_s']}, p95={aggregate['score']['p95_s']}",
        (
            f"- validate_dataset: p50={aggregate['validate_dataset']['p50_s']}, "
            f"p95={aggregate['validate_dataset']['p95_s']}"
        ),
        (
            f"- evaluate_scoring: p50={aggregate['evaluate_scoring']['p50_s']}, "
            f"p95={aggregate['evaluate_scoring']['p95_s']}"
        ),
        "",
        "## SLO Assessment",
        f"- Met: {', '.join(slo_assessment['met']) or 'none'}",
        f"- Missed: {', '.join(slo_assessment['missed']) or 'none'}",
        f"- Deferred: {', '.join(slo_assessment['deferred']) or 'none'}",
        "",
        "## Follow-ups (Week 3/4)",
    ]
    summary_lines.extend(f"- {item}" for item in metrics["week3_week4_followups"])
    summary_path = base_dir / "baseline_summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    metrics["metrics_path"] = str(metrics_path.resolve())
    metrics["summary_path"] = str(summary_path.resolve())
    return metrics
