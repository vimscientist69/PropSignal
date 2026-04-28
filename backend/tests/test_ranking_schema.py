from __future__ import annotations

import pytest
from app.schemas.ranking import (
    ErrorResponse,
    ListingDetailResponse,
    ProfileDetailResponse,
    ProfileSummaryResponse,
    RankingQueryRequest,
    RankingQueryResponse,
    StrategyPreset,
)
from pydantic import ValidationError


def _valid_request_payload() -> dict:
    return {
        "dataset_sources": ["sample-a", "sample-b"],
        "filters": {
            "province": "Western Cape",
            "price_min": 1_000_000,
            "price_max": 3_000_000,
            "confidence_min": 0.4,
        },
        "strategy": {
            "preset": "rental_income",
            "weight_overrides": {"roi_proxy": 0.35},
        },
        "result_window": {"page": 1, "page_size": 20},
        "sort_mode": "score_desc",
    }


def _valid_response_payload() -> dict:
    return {
        "run_id": "run-123",
        "query_fingerprint": "fp-123",
        "resolved_profile": {
            "profile_id": "rental-income-v1",
            "profile_version": "v1",
            "resolved_weights": {"roi_proxy": 0.35, "price_vs_comp": 0.25},
            "enabled_signals": ["roi_proxy", "price_vs_comp"],
        },
        "dataset_context": {
            "selected_sources": ["sample-a", "sample-b"],
            "records_considered": 120,
            "last_ingested_at": "2026-04-28T10:00:00Z",
            "last_scored_at": "2026-04-28T10:05:00Z",
            "model_version": "advanced_v2",
            "profile_version": "v1",
        },
        "results": [
            {
                "listing_id": 101,
                "score": 83.5,
                "deal_reason": "Strong comp discount with stable confidence.",
                "confidence": 0.81,
                "summary": {"price": 2_450_000, "city": "Cape Town"},
                "detail_ref": "run-123:listing-101",
            }
        ],
        "pagination": {
            "mode": "pagination",
            "page": 1,
            "page_size": 20,
            "total_count": 120,
        },
    }


def test_ranking_query_request_validates_valid_payload() -> None:
    model = RankingQueryRequest.model_validate(_valid_request_payload())
    assert model.strategy.preset == StrategyPreset.rental_income
    assert model.result_window.page == 1
    assert model.result_window.page_size == 20


@pytest.mark.parametrize(
    "payload_patch",
    [
        {"dataset_sources": []},
        {"dataset_sources": [""]},
        {"sort_mode": "score_asc"},
    ],
)
def test_ranking_query_request_rejects_invalid_top_level_values(payload_patch: dict) -> None:
    payload = _valid_request_payload() | payload_patch
    with pytest.raises(ValidationError):
        RankingQueryRequest.model_validate(payload)


def test_ranking_query_request_rejects_price_min_above_price_max() -> None:
    payload = _valid_request_payload()
    payload["filters"]["price_min"] = 5_000_000
    payload["filters"]["price_max"] = 3_000_000
    with pytest.raises(ValidationError):
        RankingQueryRequest.model_validate(payload)


def test_ranking_query_request_rejects_invalid_result_window_combinations() -> None:
    payload = _valid_request_payload()
    payload["result_window"] = {"top_n": 10, "page": 1, "page_size": 20}
    with pytest.raises(ValidationError):
        RankingQueryRequest.model_validate(payload)

    payload = _valid_request_payload()
    payload["result_window"] = {"page": 1}
    with pytest.raises(ValidationError):
        RankingQueryRequest.model_validate(payload)


def test_ranking_query_response_validates_pagination_envelope() -> None:
    model = RankingQueryResponse.model_validate(_valid_response_payload())
    assert model.pagination is not None
    assert model.top_n is None


def test_ranking_query_response_validates_top_n_envelope() -> None:
    payload = _valid_response_payload()
    payload.pop("pagination")
    payload["top_n"] = {
        "mode": "top_n",
        "top_n_requested": 10,
        "top_n_returned": 10,
    }
    model = RankingQueryResponse.model_validate(payload)
    assert model.top_n is not None
    assert model.pagination is None


def test_ranking_query_response_rejects_missing_or_ambiguous_envelope() -> None:
    payload = _valid_response_payload()
    payload.pop("pagination")
    with pytest.raises(ValidationError):
        RankingQueryResponse.model_validate(payload)

    payload = _valid_response_payload()
    payload["top_n"] = {
        "mode": "top_n",
        "top_n_requested": 10,
        "top_n_returned": 10,
    }
    with pytest.raises(ValidationError):
        RankingQueryResponse.model_validate(payload)


def test_listing_detail_profile_and_error_contracts_validate() -> None:
    detail = ListingDetailResponse.model_validate(
        {
            "listing_core": {"listing_id": 101},
            "score_summary": {"score": 83.5},
            "diagnostics": {"signals": [{"name": "roi_proxy"}]},
        }
    )
    assert detail.listing_core["listing_id"] == 101

    profile_summary = ProfileSummaryResponse.model_validate(
        {
            "preset": "balanced_long_term",
            "label": "Balanced Long-Term Hold",
            "description": "General long-term investing profile.",
        }
    )
    assert profile_summary.preset == StrategyPreset.balanced_long_term

    profile_detail = ProfileDetailResponse.model_validate(
        {
            "preset": "resale_arbitrage",
            "profile_id": "resale-arb-v1",
            "profile_version": "v1",
            "default_weights": {"price_vs_comp": 0.4, "roi_proxy": 0.2},
            "enabled_signals": ["price_vs_comp", "roi_proxy"],
            "safe_override_bounds": {
                "price_vs_comp": {"min": 0.3, "max": 0.5},
                "roi_proxy": {"min": 0.1, "max": 0.3},
            },
        }
    )
    assert profile_detail.preset == StrategyPreset.resale_arbitrage

    error = ErrorResponse.model_validate(
        {
            "code": "validation_error",
            "message": "Invalid request payload.",
            "field_errors": [{"field": "result_window.page", "reason": "must be >= 1"}],
            "request_id": "req-123",
        }
    )
    assert error.field_errors[0].field == "result_window.page"
