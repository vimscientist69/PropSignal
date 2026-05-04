"""Shared fixtures for Week 3 ranking integration tests."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing
from sqlalchemy.orm import Session


def seed_two_job_ranking_dataset(session: Session) -> tuple[int, int, int, int]:
    """Create two ingestion jobs with listings.

    Returns ``(job1_id, job2_id, min_listing_pk, max_listing_pk)`` for stable id assertions.
    """
    j1 = IngestionJob(
        input_path="/fixtures/ranking-seed-a.json",
        status="completed",
        records_total=2,
        records_valid=2,
        records_invalid=0,
        finished_at=datetime(2026, 4, 28, 10, 0, 0, tzinfo=UTC),
    )
    j2 = IngestionJob(
        input_path="/fixtures/ranking-seed-b.json",
        status="completed",
        records_total=1,
        records_valid=1,
        records_invalid=0,
        finished_at=datetime(2026, 4, 28, 11, 0, 0, tzinfo=UTC),
    )
    session.add_all([j1, j2])
    session.flush()

    listings = [
        Listing(
            job_id=j1.id,
            source_hash="hash-a1",
            title="Affordable Claremont",
            price=1_800_000,
            location="Claremont, Cape Town",
            bedrooms=2,
            bathrooms=1.0,
            property_type="House",
            description="Cozy",
            suburb="Claremont",
            city="Cape Town",
            province="Western Cape",
            date_posted=datetime(2026, 3, 1).date(),
            floor_size=90.0,
            normalized_payload={},
        ),
        Listing(
            job_id=j1.id,
            source_hash="hash-a2",
            title="Premium Claremont",
            price=3_200_000,
            location="Claremont, Cape Town",
            bedrooms=4,
            bathrooms=2.0,
            property_type="House",
            description="Spacious",
            suburb="Claremont",
            city="Cape Town",
            province="Western Cape",
            date_posted=datetime(2026, 2, 15).date(),
            floor_size=180.0,
            normalized_payload={},
        ),
        Listing(
            job_id=j2.id,
            source_hash="hash-b1",
            title="Sea Point flat",
            price=2_400_000,
            location="Sea Point, Cape Town",
            bedrooms=2,
            bathrooms=2.0,
            property_type="Apartment",
            description="Sea views",
            suburb="Sea Point",
            city="Cape Town",
            province="Western Cape",
            date_posted=datetime(2026, 1, 10).date(),
            floor_size=75.0,
            normalized_payload={},
        ),
    ]
    session.add_all(listings)
    session.commit()

    ids = sorted(L.id for L in listings)
    low, _, high = ids[0], ids[1], ids[2]
    return j1.id, j2.id, low, high
