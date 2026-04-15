from pathlib import Path

from app.db.base import Base
from app.models.listing import Listing
from app.models.raw_listing import RawListing
from app.models.rejected_listing import RejectedListing
from app.services.ingestion import ingest_propflux_file
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "propflux"


def _make_db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    return session_local()


def test_ingestion_partial_accept_persists_valid_and_rejected_records() -> None:
    with _make_db_session() as db:
        job = ingest_propflux_file(db, FIXTURE_DIR / "mixed_valid_invalid.json")

        assert job.status == "completed_with_errors"
        assert job.records_total == 3
        assert job.records_valid == 1
        assert job.records_invalid == 2

        raw_count = db.scalar(select(func.count()).select_from(RawListing))
        rejected_count = db.scalar(select(func.count()).select_from(RejectedListing))
        listing_count = db.scalar(select(func.count()).select_from(Listing))
        assert raw_count == 3
        assert rejected_count == 2
        assert listing_count == 1


def test_ingestion_dedup_upserts_duplicate_records() -> None:
    with _make_db_session() as db:
        job = ingest_propflux_file(db, FIXTURE_DIR / "duplicate_records.json")
        assert job.records_valid == 2
        assert job.records_invalid == 0

        listings = db.scalars(select(Listing)).all()
        assert len(listings) == 1
        assert listings[0].title == "3 Bedroom House in Blanco Updated"
