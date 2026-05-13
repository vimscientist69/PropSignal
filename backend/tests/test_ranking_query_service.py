from __future__ import annotations

from pathlib import Path

import pytest
from app.models.ranking_run import RankingRun
from app.models.ranking_run_listing import RankingRunListing
from app.models.scoring_profile_backup import ScoringProfileBackup
from app.schemas.ranking import RankingQueryRequest, StrategyPreset
from app.services.ranking_query import (
    get_listing_detail,
    list_profiles,
    resolve_profile,
    run_ranking_query,
)
from sqlalchemy.orm import Session

from tests.ranking_test_seed import seed_two_job_ranking_dataset


@pytest.fixture()
def ranking_db(db_session: Session) -> Session:
    seed_two_job_ranking_dataset(db_session)
    return db_session


def _request_payload() -> dict:
    return {
        "dataset_sources": ["1", "2"],
        "filters": {"city": "Cape Town", "property_type": "House"},
        "strategy": {"preset": "rental_income", "weight_overrides": {}},
        "result_window": {"page": 1, "page_size": 20},
        "sort_mode": "score_desc",
    }


def test_list_profiles_returns_supported_presets() -> None:
    profiles = list_profiles()
    presets = {profile.preset for profile in profiles}
    assert presets == {
        StrategyPreset.rental_income,
        StrategyPreset.resale_arbitrage,
        StrategyPreset.refurbishment_value_add,
        StrategyPreset.balanced_long_term,
    }


def test_resolve_profile_applies_override_and_normalizes() -> None:
    resolved = resolve_profile(
        StrategyPreset.rental_income,
        {"roi_proxy": 0.55},
    )
    assert resolved.profile_id == "rental_income_default"
    assert resolved.profile_version == "v1"
    assert sum(resolved.default_weights.values()) == pytest.approx(1.0, abs=1e-5)


def test_resolve_profile_rejects_unknown_signal_override() -> None:
    with pytest.raises(ValueError, match="Unknown override signal"):
        resolve_profile(StrategyPreset.rental_income, {"unknown_signal": 0.1})


def test_resolve_profile_rejects_out_of_bounds_override() -> None:
    with pytest.raises(ValueError, match="must be between"):
        resolve_profile(StrategyPreset.rental_income, {"roi_proxy": 0.99})


def test_resolve_profile_uses_alias_mapped_profile_ids() -> None:
    resolved = resolve_profile(StrategyPreset.resale_arbitrage)
    assert resolved.profile_id == "resale_arbitrage_default"
    assert resolved.enabled_signals == [
        "price_vs_comp",
        "size_vs_comp",
        "time_on_market",
        "confidence",
    ]


def test_resolve_profile_from_env_path_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "scoring_profiles.yaml"
    config_path.write_text(
        "\n".join(
            [
                "profiles:",
                "  rental_income_custom:",
                "    profile_id: rental_income_custom",
                "    label: Rental Income Custom",
                "    description: Custom profile for test",
                "    enabled_signals:",
                "      - roi_proxy",
                "      - confidence",
                "    weights:",
                "      roi_proxy: 0.7",
                "      confidence: 0.3",
                "preset_alias_mapping:",
                "  rental_income: rental_income_custom",
                "  resale_arbitrage: resale_arbitrage_default",
                "  refurbishment_value_add: refurbishment_value_add_default",
                "  balanced_long_term: balanced_long_term_default",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SCORING_PROFILES_PATH", str(config_path))
    resolved = resolve_profile(StrategyPreset.rental_income)
    assert resolved.profile_id == "rental_income_custom"
    assert resolved.default_weights == {"roi_proxy": 0.7, "confidence": 0.3}


def test_run_ranking_query_requires_db() -> None:
    request = RankingQueryRequest.model_validate(_request_payload())
    with pytest.raises(ValueError, match="requires db"):
        run_ranking_query(request)


def test_run_ranking_query_is_deterministic_for_same_request(ranking_db: Session) -> None:
    request = RankingQueryRequest.model_validate(_request_payload())
    first = run_ranking_query(request, db=ranking_db)
    second = run_ranking_query(request, db=ranking_db)
    assert first.run_id != second.run_id
    assert first.query_fingerprint == second.query_fingerprint
    assert first.dataset_context.model_version == "advanced_v2"
    assert first.dataset_context.profile_version == "v1"


def test_run_ranking_query_supports_top_n_envelope(ranking_db: Session) -> None:
    payload = _request_payload()
    payload["filters"] = {}
    payload["result_window"] = {"top_n": 5}
    request = RankingQueryRequest.model_validate(payload)
    response = run_ranking_query(request, db=ranking_db)
    assert response.top_n is not None
    assert response.pagination is None
    assert response.top_n.top_n_requested == 5


def test_get_listing_detail_returns_snapshot(ranking_db: Session) -> None:
    payload = _request_payload()
    payload["filters"] = {}
    request = RankingQueryRequest.model_validate(payload)
    response = run_ranking_query(request, db=ranking_db)
    listing_id = response.results[0].listing_id
    detail = get_listing_detail(response.run_id, listing_id, ranking_db)
    assert detail.listing_core["run_id"] == response.run_id
    assert detail.listing_core["id"] == listing_id
    assert detail.score_summary["model_version"] == "advanced_v2"
    assert detail.score_summary["profile_version"] == "v1"
    assert "signals" in detail.diagnostics


def test_run_ranking_query_persists_profile_and_run(ranking_db: Session) -> None:
    request = RankingQueryRequest.model_validate(_request_payload())
    response = run_ranking_query(request, db=ranking_db)

    run = ranking_db.query(RankingRun).filter(RankingRun.run_id == response.run_id).one_or_none()
    assert run is not None
    assert run.resolved_profile_id == "rental_income_default"
    assert response.resolved_profile.profile_row_id == run.profile_row_id
    assert run.result_count == len(response.results)
    assert run.records_considered == response.dataset_context.records_considered

    backup = (
        ranking_db.query(ScoringProfileBackup)
        .filter(ScoringProfileBackup.id == run.profile_row_id)
        .one_or_none()
    )
    assert backup is not None
    assert backup.profile_id == "rental_income_default"

    rows = (
        ranking_db.query(RankingRunListing).filter(RankingRunListing.ranking_run_id == run.id).all()
    )
    assert len(rows) == len(response.results)


def test_run_ranking_query_reuses_equivalent_profile_backup(ranking_db: Session) -> None:
    request = RankingQueryRequest.model_validate(_request_payload())
    first = run_ranking_query(request, db=ranking_db)
    second = run_ranking_query(request, db=ranking_db)

    first_run = ranking_db.query(RankingRun).filter(RankingRun.run_id == first.run_id).one()
    second_run = ranking_db.query(RankingRun).filter(RankingRun.run_id == second.run_id).one()
    assert first_run.profile_row_id == second_run.profile_row_id

    backup_count = ranking_db.query(ScoringProfileBackup).count()
    assert backup_count == 1


def test_run_ranking_query_rejects_unknown_dataset_source(ranking_db: Session) -> None:
    payload = _request_payload()
    payload["dataset_sources"] = ["no-such-job-path.json"]
    request = RankingQueryRequest.model_validate(payload)
    with pytest.raises(ValueError, match="Unknown dataset source"):
        run_ranking_query(request, db=ranking_db)
