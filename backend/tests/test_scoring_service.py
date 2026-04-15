from pathlib import Path

from app.db.base import Base
from app.models.score_result import ScoreResult
from app.services.ingestion import ingest_propflux_file
from app.services.scoring import run_scoring_job
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "propflux"


def _make_db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    return session_local()


def test_run_scoring_job_writes_baseline_score_results() -> None:
    with _make_db_session() as db:
        job = ingest_propflux_file(db, FIXTURE_DIR / "valid_listings.json")
        scored_job = run_scoring_job(db, job.id)

        assert scored_job.id == job.id
        results = db.scalars(select(ScoreResult).where(ScoreResult.job_id == job.id)).all()
        assert len(results) == 1
        result = results[0]
        assert 0.0 <= result.score <= 100.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.model_version == "baseline_v1"
        assert result.deal_reason != ""


def test_run_scoring_job_is_idempotent_for_same_job() -> None:
    with _make_db_session() as db:
        job = ingest_propflux_file(db, FIXTURE_DIR / "duplicate_records.json")
        run_scoring_job(db, job.id)
        run_scoring_job(db, job.id)

        score_count = db.scalar(
            select(func.count()).select_from(ScoreResult).where(ScoreResult.job_id == job.id)
        )
        assert score_count == 1
