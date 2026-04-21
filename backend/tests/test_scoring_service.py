from pathlib import Path

from app.models.score_result import ScoreResult
from app.services.ingestion import ingest_propflux_file
from app.services.scoring import run_scoring_job
from sqlalchemy import func, select
from sqlalchemy.orm import Session

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "propflux"


def test_run_scoring_job_writes_baseline_score_results(db_session: Session) -> None:
    job = ingest_propflux_file(db_session, FIXTURE_DIR / "valid_listings.json")
    scored_job = run_scoring_job(db_session, job.id)

    assert scored_job.id == job.id
    results = db_session.scalars(select(ScoreResult).where(ScoreResult.job_id == job.id)).all()
    assert len(results) == 1
    result = results[0]
    assert 0.0 <= result.score <= 100.0
    assert 0.0 <= result.confidence <= 1.0
    assert result.model_version in {"baseline_v1", "advanced_v2"}
    assert result.deal_reason != ""
    assert result.explanation is not None
    assert result.explanation["score_math"]["final_score_0_to_100"] == result.score
    weighted_sum = sum(float(row["weighted_contribution"]) for row in result.explanation["signals"])
    assert round(weighted_sum, 6) == result.explanation["score_math"]["weighted_sum_0_to_1"]


def test_run_scoring_job_is_idempotent_for_same_job(db_session: Session) -> None:
    job = ingest_propflux_file(db_session, FIXTURE_DIR / "duplicate_records.json")
    run_scoring_job(db_session, job.id)
    run_scoring_job(db_session, job.id)

    score_count = db_session.scalar(
        select(func.count()).select_from(ScoreResult).where(ScoreResult.job_id == job.id)
    )
    assert score_count == 1
