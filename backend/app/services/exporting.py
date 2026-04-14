from pathlib import Path

from sqlalchemy.orm import Session

from app.models.ingestion_job import IngestionJob


def export_job_results(db: Session, job_id: int, output_format: str) -> Path:
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise ValueError(f"Ingestion job not found: {job_id}")

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"job_{job_id}.{output_format}"
    output_path.write_text(
        f'{{"job_id": {job_id}, "status": "{job.status}", "format": "{output_format}"}}',
        encoding="utf-8",
    )
    return output_path
