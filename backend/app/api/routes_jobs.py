from pathlib import Path

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.db.session import SessionLocal
from app.services.ingestion import ingest_propflux_file

router = APIRouter(tags=["jobs"])


class IngestionTriggerRequest(BaseModel):
    input_path: str


@router.post("/jobs/ingest", status_code=status.HTTP_202_ACCEPTED)
def trigger_ingestion(request: IngestionTriggerRequest) -> dict[str, int | str]:
    with SessionLocal() as db:
        job = ingest_propflux_file(db, Path(request.input_path))
    return {
        "status": "accepted",
        "job_id": job.id,
        "records_total": job.records_total,
        "records_valid": job.records_valid,
        "records_invalid": job.records_invalid,
        "job_status": job.status,
    }
