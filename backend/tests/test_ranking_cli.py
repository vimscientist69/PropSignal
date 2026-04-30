from __future__ import annotations

import json
from pathlib import Path

from app.cli import app
from typer.testing import CliRunner


def _parse_json_from_output(stdout: str) -> dict:
    lines = [line for line in stdout.strip().splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("{"):
            return json.loads(line)
    raise AssertionError("Expected JSON object in CLI output.")


def test_rank_query_runs_with_schema_aligned_payload(tmp_path: Path) -> None:
    runner = CliRunner()
    output_file = tmp_path / "ranking-response.json"

    result = runner.invoke(
        app,
        [
            "rank-query",
            "--dataset-source",
            "sample-a",
            "--dataset-source",
            "sample-b",
            "--strategy-preset",
            "rental_income",
            "--city",
            "Cape Town",
            "--page",
            "1",
            "--page-size",
            "20",
            "--weight-override",
            "roi_proxy=0.36",
            "--output-json",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert "Ranking completed: run_id=" in result.stdout
    payload = _parse_json_from_output(result.stdout)
    assert payload["resolved_profile"]["profile_id"].startswith("strategy-profile-")
    assert payload["dataset_context"]["selected_sources"] == ["sample-a", "sample-b"]
    assert output_file.exists()


def test_rank_query_rejects_invalid_weight_override_format() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "rank-query",
            "--dataset-source",
            "sample-a",
            "--strategy-preset",
            "rental_income",
            "--weight-override",
            "roi_proxy:0.2",
        ],
    )

    assert result.exit_code == 2


def test_listing_detail_outputs_payload() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["listing-detail", "--run-id", "placeholder-run-abc", "--listing-id", "123"],
    )
    assert result.exit_code == 0
    assert "Listing detail loaded" in result.stdout
    payload = _parse_json_from_output(result.stdout)
    assert payload["listing_core"]["run_id"] == "placeholder-run-abc"
    assert payload["listing_core"]["listing_id"] == 123


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
