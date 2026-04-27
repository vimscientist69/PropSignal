from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing
from app.models.score_result import ScoreResult
from app.services import scoring
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _build_listing(job_id: int, source_hash: str, **overrides: object) -> Listing:
    base = {
        "job_id": job_id,
        "source_hash": source_hash,
        "title": "Test listing",
        "price": 1_000_000.0,
        "location": "test location",
        "bedrooms": 3,
        "bathrooms": 2.0,
        "property_type": "house",
        "description": "desc",
        "listing_id": f"LIST-{source_hash[-4:]}",
        "source_site": "propflux",
        "city": "Cape Town",
        "province": "Western Cape",
        "floor_size": 100.0,
        "erf_size": 200.0,
        "date_posted": date.today() - timedelta(days=30),
        "normalized_payload": {"title": "Test listing"},
    }
    base.update(overrides)
    return Listing(**base)


def test_clamp_and_days_on_market_edge_cases() -> None:
    assert scoring._clamp(-0.5) == 0.0
    assert scoring._clamp(2.5) == 1.0
    assert scoring._clamp(0.3) == 0.3

    assert scoring._days_on_market(None) is None
    future_date = datetime.now(UTC).date() + timedelta(days=10)
    assert scoring._days_on_market(future_date) == 0


def test_load_scoring_config_returns_defaults_without_config_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    config = scoring._load_scoring_config()

    assert config["weights"]["price_deviation"] == 0.35
    assert config["rules"]["stale_inventory_days"] == 90
    assert config["advanced_v2"]["comps"]["fallback_order"] == [
        "suburb",
        "city",
        "province",
        "global",
    ]
    assert (
        config["evaluation_thresholds"]["stability"]["segments"]["top_band"]["jaccard_min"] == 0.7
    )


def test_load_scoring_config_deep_merges_advanced_v2_and_threshold_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "scoring.yaml").write_text(
        "\n".join(
            [
                "weights:",
                "  confidence: 0.15",
                "advanced_v2:",
                "  comps:",
                "    minimum_cohort_size: 20",
                "  roi:",
                "    transaction_cost_pct: 0.1",
                "evaluation_thresholds:",
                "  stability:",
                "    segments:",
                "      top_band:",
                "        rank_correlation_min: 0.85",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    config = scoring._load_scoring_config()
    assert config["weights"]["confidence"] == 0.15
    assert config["weights"]["price_deviation"] == 0.35
    assert config["advanced_v2"]["comps"]["minimum_cohort_size"] == 20
    assert config["advanced_v2"]["comps"]["fallback_order"] == [
        "suburb",
        "city",
        "province",
        "global",
    ]
    assert config["advanced_v2"]["roi"]["transaction_cost_pct"] == 0.1
    assert config["advanced_v2"]["roi"]["maintenance_pct"] == 0.04
    assert (
        config["evaluation_thresholds"]["stability"]["segments"]["top_band"]["rank_correlation_min"]
        == 0.85
    )
    assert (
        config["evaluation_thresholds"]["stability"]["segments"]["top_band"]["jaccard_min"] == 0.7
    )


def test_signal_neutral_defaults_when_inputs_missing() -> None:
    listing = _build_listing(
        job_id=1,
        source_hash="hash-neutral",
        floor_size=None,
        date_posted=None,
    )

    assert scoring._price_deviation_signal(listing, 0.0) == 0.5
    assert scoring._size_value_signal(listing, median_price_per_sqm=0.0) == 0.5
    assert scoring._time_on_market_signal(listing, stale_inventory_days=0) == 0.5


def test_resolve_comp_context_excludes_subject_listing() -> None:
    target = _build_listing(1, "hash-target", listing_id="L-1", id=1)
    peer_a = _build_listing(1, "hash-peer-a", listing_id="L-2", id=2)
    peer_b = _build_listing(1, "hash-peer-b", listing_id="L-3", id=3)
    listings = [target, peer_a, peer_b]

    comp_index = scoring._build_comp_index(
        listings=listings,
        fallback_order=["suburb", "city", "province", "global"],
        include_bedrooms=True,
        include_bathrooms=True,
    )
    _level, comparable, _penalty = scoring._resolve_comp_context(
        listing=target,
        comp_index=comp_index,
        fallback_order=["suburb", "city", "province", "global"],
        minimum_cohort_size=2,
        include_bedrooms=True,
        include_bathrooms=True,
    )
    comparable_ids = {row.id for row in comparable}
    assert 1 not in comparable_ids
    assert comparable_ids == {2, 3}


def test_resolve_comp_context_falls_back_when_suburb_cohort_too_small() -> None:
    target = _build_listing(1, "hash-target", id=1, suburb="UniqueSuburb")
    peer_a = _build_listing(1, "hash-peer-a", id=2, suburb="OtherSuburb")
    peer_b = _build_listing(1, "hash-peer-b", id=3, suburb="OtherSuburb")
    listings = [target, peer_a, peer_b]

    comp_index = scoring._build_comp_index(
        listings=listings,
        fallback_order=["suburb", "city", "province", "global"],
        include_bedrooms=False,
        include_bathrooms=False,
    )
    level, comparable, penalty = scoring._resolve_comp_context(
        listing=target,
        comp_index=comp_index,
        fallback_order=["suburb", "city", "province", "global"],
        minimum_cohort_size=2,
        include_bedrooms=False,
        include_bathrooms=False,
    )
    assert level == "city"
    assert len(comparable) == 2
    assert penalty == 0.03


def test_roi_proxy_signal_is_deterministic_and_bounded() -> None:
    listing = _build_listing(
        1,
        "hash-roi",
        property_type="Apartment",
        rates_and_taxes=1200.0,
        levies=1500.0,
    )
    roi_config = {
        "transaction_cost_pct": 0.08,
        "vacancy_allowance_pct": 0.05,
        "maintenance_pct": 0.04,
        "management_pct": 0.08,
        "insurance_pct": 0.01,
    }
    signal_one = scoring._roi_proxy_signal(listing, roi_config)
    signal_two = scoring._roi_proxy_signal(listing, roi_config)
    assert signal_one == signal_two
    assert 0.0 <= signal_one <= 1.0


def test_confidence_signal_reflects_completeness() -> None:
    full = _build_listing(job_id=1, source_hash="hash-full", agent_name="Agent One")
    sparse = _build_listing(
        job_id=1,
        source_hash="hash-sparse",
        date_posted=None,
        floor_size=None,
        erf_size=None,
        listing_id=None,
        source_site=None,
        city=None,
        province=None,
        agent_name=None,
    )

    assert scoring._confidence_signal(full) == 1.0
    assert scoring._confidence_signal(sparse) == 0.0


def test_deal_reason_fallback_and_reason_order() -> None:
    fallback = scoring._deal_reason(
        price_signal=0.5,
        size_signal=0.5,
        time_signal=0.5,
        feature_signal=0.5,
        confidence_signal=0.7,
    )
    assert fallback == "Baseline composite score from normalized listing attributes"

    reason = scoring._deal_reason(
        price_signal=0.8,
        size_signal=0.8,
        time_signal=0.8,
        feature_signal=0.8,
        confidence_signal=0.2,
    )
    # Only top three should be included.
    assert "Price is favorable versus dataset median" in reason
    assert "Strong size-to-price profile" in reason
    assert "Extended time on market may indicate seller pressure" in reason
    assert "Feature density supports value" not in reason


def test_run_scoring_job_raises_for_missing_job(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Ingestion job not found"):
        scoring.run_scoring_job(db_session, 999)


def test_run_scoring_job_raises_when_job_has_no_listings(db_session: Session) -> None:
    job = IngestionJob(input_path="dummy.json", status="processing")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    with pytest.raises(ValueError, match="No listings found"):
        scoring.run_scoring_job(db_session, job.id)


def test_run_scoring_job_writes_result_per_listing_and_idempotent(db_session: Session) -> None:
    job = IngestionJob(input_path="dummy.json", status="processing")
    db_session.add(job)
    db_session.flush()

    listing_a = _build_listing(job.id, "hash-a", listing_id="A-1", price=900_000.0)
    listing_b = _build_listing(job.id, "hash-b", listing_id="B-1", price=1_200_000.0)
    db_session.add_all([listing_a, listing_b])
    db_session.commit()

    scoring.run_scoring_job(db_session, job.id)
    scoring.run_scoring_job(db_session, job.id)

    count = db_session.scalar(
        select(func.count()).select_from(ScoreResult).where(ScoreResult.job_id == job.id)
    )
    assert count == 2

    results = db_session.scalars(select(ScoreResult).where(ScoreResult.job_id == job.id)).all()
    assert all(0.0 <= row.score <= 100.0 for row in results)
    assert all(0.0 <= row.confidence <= 1.0 for row in results)
    assert all(row.model_version in {"baseline_v1", "advanced_v2"} for row in results)


def test_run_scoring_job_applies_config_weights(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = IngestionJob(input_path="dummy.json", status="processing")
    db_session.add(job)
    db_session.flush()
    db_session.add(_build_listing(job.id, "hash-weight", listing_id="W-1"))
    db_session.commit()

    monkeypatch.setattr(
        scoring,
        "_load_scoring_config",
        lambda: {
            "weights": {
                "price_deviation": 1.0,
                "feature_value": 0.0,
                "time_on_market": 0.0,
                "liquidity": 0.0,
                "confidence": 0.0,
            },
            "rules": {"stale_inventory_days": 90},
        },
    )
    monkeypatch.setattr(scoring, "_price_deviation_signal", lambda *_: 0.9)
    monkeypatch.setattr(scoring, "_size_value_signal", lambda *_: 0.1)
    monkeypatch.setattr(scoring, "_time_on_market_signal", lambda *_: 0.1)
    monkeypatch.setattr(scoring, "_feature_density_signal", lambda *_: 0.1)
    monkeypatch.setattr(scoring, "_confidence_signal", lambda *_: 0.1)

    scoring.run_scoring_job(db_session, job.id)
    row = db_session.scalar(select(ScoreResult).where(ScoreResult.job_id == job.id))
    assert row is not None
    assert row.score == 90.0


def test_run_scoring_job_uses_advanced_v2_when_flags_enabled(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = IngestionJob(input_path="dummy.json", status="processing")
    db_session.add(job)
    db_session.flush()
    db_session.add(_build_listing(job.id, "hash-a", listing_id="A-1", id=101))
    db_session.add(_build_listing(job.id, "hash-b", listing_id="B-1", id=102))
    db_session.add(_build_listing(job.id, "hash-c", listing_id="C-1", id=103))
    db_session.commit()

    monkeypatch.setattr(
        scoring,
        "_load_scoring_config",
        lambda: {
            "weights": {
                "price_deviation": 0.35,
                "feature_value": 0.2,
                "time_on_market": 0.2,
                "liquidity": 0.15,
                "confidence": 0.1,
            },
            "rules": {"stale_inventory_days": 90},
            "flags": {
                "enable_advanced_v2_micro_comps": True,
                "enable_advanced_v2_roi_proxy": True,
            },
            "advanced_v2": {
                "weights": {
                    "price_vs_comp": 0.3,
                    "size_vs_comp": 0.18,
                    "time_on_market": 0.14,
                    "feature_value": 0.1,
                    "confidence": 0.08,
                    "roi_proxy": 0.2,
                },
                "comps": {
                    "minimum_cohort_size": 1,
                    "fallback_order": ["suburb", "city", "province", "global"],
                    "include_bedrooms": True,
                    "include_bathrooms": True,
                },
                "roi": {
                    "transaction_cost_pct": 0.08,
                    "vacancy_allowance_pct": 0.05,
                    "maintenance_pct": 0.04,
                    "management_pct": 0.08,
                    "insurance_pct": 0.01,
                },
            },
            "evaluation_thresholds": {
                "stability": {
                    "segments": {
                        "top_band": {
                            "jaccard_min": 0.7,
                            "rank_correlation_min": 0.8,
                        }
                    },
                }
            },
        },
    )

    scoring.run_scoring_job(db_session, job.id)
    rows = db_session.scalars(select(ScoreResult).where(ScoreResult.job_id == job.id)).all()
    assert len(rows) == 3
    assert all(row.model_version == "advanced_v2" for row in rows)
    for row in rows:
        assert row.explanation is not None
        assert row.explanation["summary"]["primary_driver"] != ""
        assert row.explanation["score_math"]["final_score_0_to_100"] == row.score
        weighted_sum = sum(
            float(signal["weighted_contribution"]) for signal in row.explanation["signals"]
        )
        assert round(weighted_sum, 6) == row.explanation["score_math"]["weighted_sum_0_to_1"]
