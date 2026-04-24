from app.models.ingestion_job import IngestionJob
from app.services.analytics import run_analytics_job
from sqlalchemy.orm import Session


def test_run_analytics_job_sets_analyzed_status(db_session: Session) -> None:
    job = IngestionJob(input_path="fixture.json", status="completed")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    analyzed = run_analytics_job(db_session, job.id)
    assert analyzed.status == "analyzed"

