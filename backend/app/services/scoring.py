from sqlalchemy.orm import Session

from app.models.ingestion_job import IngestionJob


def run_scoring_job(db: Session, job_id: int) -> IngestionJob:
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise ValueError(f"Ingestion job not found: {job_id}")
    job.status = "scored"
    db.commit()
    db.refresh(job)
    return job
