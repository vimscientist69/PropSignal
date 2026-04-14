from pathlib import Path

from sqlalchemy.orm import Session

from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing
from app.schemas.propflux_listing import load_propflux_file


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


def ingest_propflux_file(db: Session, path: Path) -> IngestionJob:
    ensure_file_exists(path)
    parsed = load_propflux_file(path)

    job = IngestionJob(
        input_path=str(path),
        status="ingested",
        records_total=len(parsed),
        records_valid=len(parsed),
    )
    db.add(job)
    db.flush()

    for row in parsed:
        payload = row.model_dump()
        listing = Listing(
            job_id=job.id,
            title=row.title,
            price=row.price,
            location=row.location,
            bedrooms=row.bedrooms,
            bathrooms=row.bathrooms,
            property_type=row.property_type,
            description=row.description,
            agent_name=row.agent_name,
            agent_phone=row.agent_phone,
            agency_name=row.agency_name,
            listing_id=row.listing_id,
            date_posted=row.date_posted,
            erf_size=row.erf_size,
            floor_size=row.floor_size,
            rates_and_taxes=row.rates_and_taxes,
            levies=row.levies,
            garages=row.garages,
            parking=row.parking,
            en_suite=row.en_suite,
            lounges=row.lounges,
            backup_power=row.backup_power,
            security=row.security,
            pets_allowed=row.pets_allowed,
            listing_url=row.listing_url,
            suburb=row.suburb,
            city=row.city,
            province=row.province,
            is_auction=row.is_auction,
            is_private_seller=row.is_private_seller,
            source_site=row.source_site,
            scraped_at=row.scraped_at,
            raw_payload=payload,
        )
        db.add(listing)

    db.commit()
    db.refresh(job)
    return job
