from __future__ import annotations

import pytest
from app.db.base import Base
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.ranking_test_seed import seed_two_job_ranking_dataset


@pytest.fixture()
def ranking_api_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from app.api import routes_ranking, routes_runs_diagnostics

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session_local = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, class_=Session
    )
    with test_session_local() as session:
        seed_two_job_ranking_dataset(session)
    monkeypatch.setattr(routes_ranking, "SessionLocal", test_session_local)
    monkeypatch.setattr(routes_runs_diagnostics, "SessionLocal", test_session_local)
    return TestClient(app)


def test_rankings_query_validation_returns_error_envelope() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/rankings/query",
        json={
            "dataset_sources": [],
            "filters": {},
            "strategy": {"preset": "rental_income"},
            "result_window": {"page": 1, "page_size": 20},
            "sort_mode": "score_desc",
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "validation_error"
    assert "message" in data
    assert "field_errors" in data
    assert "request_id" in data


def test_rankings_query_price_bounds_validation() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/rankings/query",
        json={
            "dataset_sources": ["1"],
            "filters": {"price_min": 500, "price_max": 100},
            "strategy": {"preset": "rental_income"},
            "result_window": {"page": 1, "page_size": 20},
            "sort_mode": "score_desc",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_rankings_query_unknown_dataset_source(ranking_api_client: TestClient) -> None:
    response = ranking_api_client.post(
        "/api/v1/rankings/query",
        json={
            "dataset_sources": ["/nope/not-a-job.json"],
            "filters": {},
            "strategy": {"preset": "rental_income"},
            "result_window": {"page": 1, "page_size": 20},
            "sort_mode": "score_desc",
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "unknown_dataset_source"


def test_rankings_query_success(ranking_api_client: TestClient) -> None:
    response = ranking_api_client.post(
        "/api/v1/rankings/query",
        json={
            "dataset_sources": ["1"],
            "filters": {"city": "Cape Town"},
            "strategy": {"preset": "rental_income", "weight_overrides": {}},
            "result_window": {"page": 1, "page_size": 20},
            "sort_mode": "score_desc",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["resolved_profile"]["profile_id"] == "rental_income_default"
    assert len(data["results"]) >= 1
    assert data["dataset_context"]["records_considered"] >= 1


def test_listing_detail_not_found(ranking_api_client: TestClient) -> None:
    response = ranking_api_client.get("/api/v1/rankings/missing-run/listings/1")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert "request_id" in body


def test_listing_detail_after_ranking(ranking_api_client: TestClient) -> None:
    rank = ranking_api_client.post(
        "/api/v1/rankings/query",
        json={
            "dataset_sources": ["1", "2"],
            "filters": {},
            "strategy": {"preset": "balanced_long_term"},
            "result_window": {"top_n": 5},
            "sort_mode": "score_desc",
        },
    )
    assert rank.status_code == 200
    run_id = rank.json()["run_id"]
    listing_id = rank.json()["results"][0]["listing_id"]
    detail = ranking_api_client.get(f"/api/v1/rankings/{run_id}/listings/{listing_id}")
    assert detail.status_code == 200
    core = detail.json()["listing_core"]
    assert core["run_id"] == run_id
    assert core["id"] == listing_id
    assert "title" in core
    assert "normalized_payload" in core


def test_ranking_results_include_table_fields(ranking_api_client: TestClient) -> None:
    response = ranking_api_client.post(
        "/api/v1/rankings/query",
        json={
            "dataset_sources": ["1"],
            "filters": {},
            "strategy": {"preset": "rental_income", "weight_overrides": {}},
            "result_window": {"top_n": 3},
            "sort_mode": "score_desc",
        },
    )
    assert response.status_code == 200
    row = response.json()["results"][0]
    assert "bedrooms" in row
    assert "bathrooms" in row
    assert "province" in row


def test_runs_list_after_ranking(ranking_api_client: TestClient) -> None:
    ranking_api_client.post(
        "/api/v1/rankings/query",
        json={
            "dataset_sources": ["1"],
            "filters": {},
            "strategy": {"preset": "rental_income", "weight_overrides": {}},
            "result_window": {"top_n": 2},
            "sort_mode": "score_desc",
        },
    )
    runs = ranking_api_client.get("/api/v1/runs?page=1&page_size=10")
    assert runs.status_code == 200
    body = runs.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1
    assert body["items"][0]["records_considered"] >= 1


def test_run_detail_and_export(ranking_api_client: TestClient) -> None:
    rank = ranking_api_client.post(
        "/api/v1/rankings/query",
        json={
            "dataset_sources": ["1", "2"],
            "filters": {},
            "strategy": {"preset": "balanced_long_term"},
            "result_window": {"top_n": 2},
            "sort_mode": "score_desc",
        },
    )
    run_id = rank.json()["run_id"]
    detail = ranking_api_client.get(f"/api/v1/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["run_id"] == run_id
    assert len(detail.json()["results"]) >= 1
    export_json = ranking_api_client.get(f"/api/v1/runs/{run_id}/export?format=json")
    assert export_json.status_code == 200
    payload = export_json.json()
    assert "export_metadata" in payload
    assert payload["export_metadata"]["run_id"] == run_id
    assert "results" in payload
    export_csv = ranking_api_client.get(f"/api/v1/runs/{run_id}/export?format=csv")
    assert export_csv.status_code == 200
    assert "export_metadata" in export_csv.text

    export_detail = ranking_api_client.get(
        f"/api/v1/runs/{run_id}/export?format=json&listing_detail=true",
    )
    assert export_detail.status_code == 200
    first = export_detail.json()["results"][0]
    assert "listing_detail" in first
    assert "listing_core" in first["listing_detail"]
    assert "score_summary" in first["listing_detail"]
    assert "diagnostics" in first["listing_detail"]


def test_diagnostics_summary(ranking_api_client: TestClient) -> None:
    response = ranking_api_client.get("/api/v1/diagnostics/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["api_status"] == "ok"
    assert body["total_listings"] >= 1


def test_scoring_profiles_list() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/scoring/profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert len(profiles) == 4
    presets = {p["preset"] for p in profiles}
    assert presets == {
        "rental_income",
        "resale_arbitrage",
        "refurbishment_value_add",
        "balanced_long_term",
    }


def test_scoring_profile_preset() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/scoring/profiles/resale_arbitrage")
    assert response.status_code == 200
    data = response.json()
    assert data["profile_id"] == "resale_arbitrage_default"
    assert data["preset"] == "resale_arbitrage"


def test_dataset_sources_summary(ranking_api_client: TestClient) -> None:
    response = ranking_api_client.get("/api/v1/datasets/sources")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    first = data[0]
    assert "source" in first
    assert "job_id" in first
    assert "status" in first
