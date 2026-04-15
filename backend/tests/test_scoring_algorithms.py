from datetime import UTC, date, datetime, timedelta

import pytest
from app.db.base import Base
from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing
from app.models.score_result import ScoreResult
from app.services import scoring
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker


def _make_db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    return session_local()


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


def test_run_scoring_job_raises_for_missing_job() -> None:
    with _make_db_session() as db:
        with pytest.raises(ValueError, match="Ingestion job not found"):
            scoring.run_scoring_job(db, 999)


def test_run_scoring_job_raises_when_job_has_no_listings() -> None:
    with _make_db_session() as db:
        job = IngestionJob(input_path="dummy.json", status="processing")
        db.add(job)
        db.commit()
        db.refresh(job)

        with pytest.raises(ValueError, match="No listings found"):
            scoring.run_scoring_job(db, job.id)


def test_run_scoring_job_writes_result_per_listing_and_idempotent() -> None:
    with _make_db_session() as db:
        job = IngestionJob(input_path="dummy.json", status="processing")
        db.add(job)
        db.flush()

        listing_a = _build_listing(job.id, "hash-a", listing_id="A-1", price=900_000.0)
        listing_b = _build_listing(job.id, "hash-b", listing_id="B-1", price=1_200_000.0)
        db.add_all([listing_a, listing_b])
        db.commit()

        scoring.run_scoring_job(db, job.id)
        scoring.run_scoring_job(db, job.id)

        count = db.scalar(
            select(func.count()).select_from(ScoreResult).where(ScoreResult.job_id == job.id)
        )
        assert count == 2

        results = db.scalars(select(ScoreResult).where(ScoreResult.job_id == job.id)).all()
        assert all(0.0 <= row.score <= 100.0 for row in results)
        assert all(0.0 <= row.confidence <= 1.0 for row in results)
        assert all(row.model_version == "baseline_v1" for row in results)


def test_run_scoring_job_applies_config_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    with _make_db_session() as db:
        job = IngestionJob(input_path="dummy.json", status="processing")
        db.add(job)
        db.flush()
        db.add(_build_listing(job.id, "hash-weight", listing_id="W-1"))
        db.commit()

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

        scoring.run_scoring_job(db, job.id)
        row = db.scalar(select(ScoreResult).where(ScoreResult.job_id == job.id))
        assert row is not None
        assert row.score == 90.0
