from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.cli import app
from app.db.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from typer.testing import CliRunner

from tests.ranking_test_seed import seed_two_job_ranking_dataset


class _TestSessionLocal:
    def __init__(self, session: Session):
        self._session = session

    def __call__(self) -> _TestSessionLocal:
        return self

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._session.rollback()
        return False


def _parse_json_from_output(stdout: str) -> dict:
    lines = [line for line in stdout.strip().splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("{"):
            return json.loads(line)
    raise AssertionError("Expected JSON object in CLI output.")


def test_rank_query_runs_with_schema_aligned_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    output_file = tmp_path / "ranking-response.json"
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    session = session_local()
    seed_two_job_ranking_dataset(session)
    monkeypatch.setattr("app.cli.SessionLocal", _TestSessionLocal(session))

    result = runner.invoke(
        app,
        [
            "rank-query",
            "--dataset-source",
            "1",
            "--dataset-source",
            "2",
            "--strategy-preset",
            "rental_income",
            "--city",
            "Cape Town",
            "--page",
            "1",
            "--page-size",
            "20",
            "--weight-override",
            "roi_proxy=0.55",
            "--output-json",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert "Ranking completed: run_id=" in result.stdout
    payload = _parse_json_from_output(result.stdout)
    assert payload["resolved_profile"]["profile_id"] == "rental_income_default"
    assert payload["dataset_context"]["selected_sources"] == ["1", "2"]
    assert output_file.exists()


def test_rank_query_rejects_invalid_weight_override_format() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "rank-query",
            "--dataset-source",
            "1",
            "--strategy-preset",
            "rental_income",
            "--weight-override",
            "roi_proxy:0.2",
        ],
    )

    assert result.exit_code == 2


def test_listing_detail_outputs_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    session = session_local()
    seed_two_job_ranking_dataset(session)
    monkeypatch.setattr("app.cli.SessionLocal", _TestSessionLocal(session))

    out_rank = tmp_path / "rank.json"
    rank = runner.invoke(
        app,
        [
            "rank-query",
            "--dataset-source",
            "1",
            "--strategy-preset",
            "rental_income",
            "--output-json",
            str(out_rank),
        ],
    )
    assert rank.exit_code == 0
    rank_payload = json.loads(out_rank.read_text(encoding="utf-8"))
    run_id = rank_payload["run_id"]
    listing_id = rank_payload["results"][0]["listing_id"]

    result = runner.invoke(
        app,
        ["listing-detail", "--run-id", run_id, "--listing-id", str(listing_id)],
    )
    assert result.exit_code == 0
    assert "Listing detail loaded" in result.stdout
    payload = _parse_json_from_output(result.stdout)
    assert payload["listing_core"]["run_id"] == run_id
    assert payload["listing_core"]["listing_id"] == listing_id


def test_profiles_list_outputs_profiles_array() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["profiles-list"])
    assert result.exit_code == 0
    assert "Profiles available: 4" in result.stdout
    payload = _parse_json_from_output(result.stdout)
    assert len(payload["profiles"]) == 4


def test_profile_show_outputs_resolved_profile() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["profile-show", "--preset", "balanced_long_term"])
    assert result.exit_code == 0
    assert "Profile resolved: preset=balanced_long_term" in result.stdout
    payload = _parse_json_from_output(result.stdout)
    assert payload["preset"] == "balanced_long_term"
