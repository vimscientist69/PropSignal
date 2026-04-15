from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing
from app.models.raw_listing import RawListing
from app.models.rejected_listing import RejectedListing
from app.schemas.propflux_listing import (
    load_propflux_payload,
    validate_propflux_payload_partial,
)
from app.services.normalization import normalize_listing


def create_ingestion_job(
    db: Session,
    input_path: str,
    records_total: int,
    records_valid: int,
) -> IngestionJob:
    job = IngestionJob(
        input_path=input_path,
        status="ingested",
        records_total=records_total,
        records_valid=records_valid,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def ensure_file_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")


def _upsert_normalized_listing(
    db: Session,
    job_id: int,
    payload: dict[str, Any],
    source_hash: str,
) -> None:
    source_site = payload.get("source_site")
    listing_id = payload.get("listing_id")

    existing: Listing | None = None
    if source_site and listing_id:
        existing = db.scalar(
            select(Listing).where(
                Listing.source_site == source_site,
                Listing.listing_id == listing_id,
            )
        )
    if existing is None:
        existing = db.scalar(select(Listing).where(Listing.source_hash == source_hash))

    data = {
        "job_id": job_id,
        "source_hash": source_hash,
        "title": payload["title"],
        "price": float(payload["price"]),
        "location": payload["location"],
        "bedrooms": int(payload["bedrooms"]),
        "bathrooms": float(payload["bathrooms"]),
        "property_type": payload["property_type"],
        "description": payload["description"],
        "agent_name": payload.get("agent_name"),
        "agent_phone": payload.get("agent_phone"),
        "agency_name": payload.get("agency_name"),
        "listing_id": payload.get("listing_id"),
        "date_posted": payload.get("date_posted"),
        "erf_size": payload.get("erf_size"),
        "floor_size": payload.get("floor_size"),
        "rates_and_taxes": payload.get("rates_and_taxes"),
        "levies": payload.get("levies"),
        "garages": payload.get("garages"),
        "parking": payload.get("parking"),
        "en_suite": payload.get("en_suite"),
        "lounges": payload.get("lounges"),
        "backup_power": payload.get("backup_power"),
        "security": payload.get("security"),
        "pets_allowed": payload.get("pets_allowed"),
        "listing_url": payload.get("listing_url"),
        "suburb": payload.get("suburb"),
        "city": payload.get("city"),
        "province": payload.get("province"),
        "is_auction": payload.get("is_auction"),
        "is_private_seller": payload.get("is_private_seller"),
        "source_site": payload.get("source_site"),
        "scraped_at": payload.get("scraped_at"),
        "normalized_payload": payload,
    }

    if existing is None:
        db.add(Listing(**data))
        return

    for key, value in data.items():
        setattr(existing, key, value)


def ingest_propflux_file(db: Session, path: Path) -> IngestionJob:
    ensure_file_exists(path)
    payload = load_propflux_payload(path)
    if not isinstance(payload, list):
        raise ValueError("PropFlux payload must be a JSON array of listing objects.")

    job = IngestionJob(
        input_path=str(path),
        status="processing",
        records_total=len(payload),
        records_valid=0,
        records_invalid=0,
        started_at=datetime.now(UTC),
    )
    db.add(job)
    db.flush()

    chunk_size = 500
    for chunk_start in range(0, len(payload), chunk_size):
        chunk = payload[chunk_start : chunk_start + chunk_size]
        valid_records, invalid_records = validate_propflux_payload_partial(chunk)

        for relative_index, raw_row in enumerate(chunk):
            absolute_index = chunk_start + relative_index
            raw_payload = raw_row if isinstance(raw_row, dict) else {"_raw": raw_row}
            db.add(
                RawListing(
                    job_id=job.id,
                    record_index=absolute_index,
                    source_site=(
                        (raw_row or {}).get("source_site") if isinstance(raw_row, dict) else None
                    ),
                    listing_id=(
                        (raw_row or {}).get("listing_id") if isinstance(raw_row, dict) else None
                    ),
                    payload=raw_payload,
                )
            )

        for error in invalid_records:
            absolute_index = chunk_start + error.record_index
            db.add(
                RejectedListing(
                    job_id=job.id,
                    record_index=absolute_index,
                    error_code=error.error_code,
                    error_detail=error.error_detail,
                    payload=error.payload,
                )
            )

        for _relative_index, record in valid_records:
            normalized = normalize_listing(record)
            _upsert_normalized_listing(
                db=db,
                job_id=job.id,
                payload=normalized.payload,
                source_hash=normalized.source_hash,
            )
            db.flush()

        job.records_valid += len(valid_records)
        job.records_invalid += len(invalid_records)
        db.flush()

    if job.records_invalid > 0:
        job.status = "completed_with_errors"
        job.error_summary = f"{job.records_invalid} records rejected during validation"
    else:
        job.status = "completed"
        job.error_summary = None

    job.finished_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job
