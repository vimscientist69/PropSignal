from __future__ import annotations

import json
from pathlib import Path

from app.services.performance_baseline import run_performance_baseline
from sqlalchemy.orm import Session

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "propflux"


def test_performance_baseline_single_dataset_writes_artifacts(
    db_session: Session, tmp_path: Path
) -> None:
    metrics = run_performance_baseline(
        db_session,
        dataset_paths=[str(FIXTURE_DIR / "valid_listings.json")],
        top_n=20,
        output_dir=str(tmp_path),
    )

    assert metrics["scope"] == "week2_phase4_minimal_baseline"
    assert len(metrics["datasets"]) == 1
    assert metrics["datasets"][0]["status"] == "pass"
    assert Path(metrics["metrics_path"]).exists()
    assert Path(metrics["summary_path"]).exists()

    saved = json.loads(Path(metrics["metrics_path"]).read_text(encoding="utf-8"))
    assert "aggregate" in saved
    assert "slo_assessment" in saved
    assert "score" in saved["aggregate"]


def test_performance_baseline_multiple_datasets_aggregates(
    db_session: Session, tmp_path: Path
) -> None:
    metrics = run_performance_baseline(
        db_session,
        dataset_paths=[
            str(FIXTURE_DIR / "valid_listings.json"),
            str(FIXTURE_DIR / "duplicate_records.json"),
        ],
        top_n=20,
        output_dir=str(tmp_path),
    )

    assert len(metrics["datasets"]) == 2
    assert all(row["status"] in {"pass", "error"} for row in metrics["datasets"])
    assert set(metrics["aggregate"].keys()) == {
        "ingest",
        "score",
        "validate_dataset",
        "evaluate_scoring",
    }
    assert "deferred" in metrics["slo_assessment"]
    assert "ranking_list_api_p95_ms" in metrics["slo_assessment"]["deferred"]
