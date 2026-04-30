from __future__ import annotations

import pytest
from app.schemas.ranking import RankingQueryRequest, StrategyPreset
from app.services.ranking_query import (
    get_listing_detail,
    list_profiles,
    resolve_profile,
    run_ranking_query,
)


def _request_payload() -> dict:
    return {
        "dataset_sources": ["sample-a", "sample-b"],
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
        {"roi_proxy": 0.36},
    )
    assert resolved.profile_id.startswith("strategy-profile-")
    assert resolved.profile_version == "v1"
    assert sum(resolved.default_weights.values()) == pytest.approx(1.0, abs=1e-5)


def test_resolve_profile_rejects_unknown_signal_override() -> None:
    with pytest.raises(ValueError, match="Unknown override signal"):
        resolve_profile(StrategyPreset.rental_income, {"unknown_signal": 0.1})


def test_run_ranking_query_is_deterministic_for_same_request() -> None:
    request = RankingQueryRequest.model_validate(_request_payload())
    first = run_ranking_query(request)
    second = run_ranking_query(request)
    assert first.run_id == second.run_id
    assert first.query_fingerprint == second.query_fingerprint
    assert first.dataset_context.model_version == "advanced_v2"
    assert first.dataset_context.profile_version == "v1"


def test_run_ranking_query_supports_top_n_envelope() -> None:
    payload = _request_payload()
    payload["result_window"] = {"top_n": 5}
    request = RankingQueryRequest.model_validate(payload)
    response = run_ranking_query(request)
    assert response.top_n is not None
    assert response.pagination is None
    assert response.top_n.top_n_requested == 5


def test_get_listing_detail_returns_expected_metadata() -> None:
    detail = get_listing_detail("placeholder-run-abc", 123)
    assert detail.listing_core["run_id"] == "placeholder-run-abc"
    assert detail.listing_core["listing_id"] == 123
    assert detail.score_summary["model_version"] == "advanced_v2"
    assert detail.score_summary["profile_version"] == "v1"
