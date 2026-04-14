from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(tags=["jobs"])


class IngestionTriggerRequest(BaseModel):
    input_path: str


@router.post("/jobs/ingest", status_code=status.HTTP_202_ACCEPTED)
def trigger_ingestion(request: IngestionTriggerRequest) -> dict[str, str]:
    # Placeholder endpoint until Week 1 ingestion orchestration is fully implemented.
    return {
        "status": "accepted",
        "message": f"Ingestion trigger received for {request.input_path}",
    }
