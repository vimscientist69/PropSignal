"""Resolve Week 3 dataset_sources strings to ingestion job ids."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing

_JOB_ID_NUMERIC = re.compile(r"^\d+$")
_JOB_ID_PREFIX = re.compile(r"^job[:/](\d+)$", re.IGNORECASE)


def resolve_dataset_sources_to_job_ids(db: Session, sources: list[str]) -> list[int]:
    """Map each source to an ingestion job id (order preserved, duplicates kept).

    Accepted forms per source token (after strip):
    - digits only: ``42`` -> job id 42
    - ``job:42`` or ``job/42`` -> job id 42
    - otherwise: exact match on ``IngestionJob.input_path`` (first row by ascending id)
    """
    job_ids: list[int] = []
    for raw in sources:
        token = raw.strip()
        resolved: int | None = None
        m = _JOB_ID_PREFIX.match(token)
        if m:
            resolved = int(m.group(1))
        elif _JOB_ID_NUMERIC.match(token):
            resolved = int(token)
        if resolved is not None:
            job = db.get(IngestionJob, resolved)
            if job is None:
                raise ValueError(
                    f"Unknown dataset source {raw!r}: ingestion job id {resolved} does not exist."
                )
            job_ids.append(resolved)
            continue

        job = db.scalar(
            select(IngestionJob)
            .where(IngestionJob.input_path == token)
            .order_by(IngestionJob.id.asc())
            .limit(1)
        )
        if job is None:
            raise ValueError(
                f"Unknown dataset source {raw!r}: no ingestion job with matching input_path "
                "or numeric job id."
            )
        job_ids.append(job.id)
    return job_ids


def merge_listings_for_jobs(db: Session, job_ids: list[int]) -> list[Listing]:
    """Load listings for jobs, dedupe by ``source_hash`` (deterministic: lowest (job_id, id))."""
    rows: list[Listing] = []
    for jid in job_ids:
        part = db.scalars(select(Listing).where(Listing.job_id == jid).order_by(Listing.id)).all()
        rows.extend(part)
    rows.sort(key=lambda L: (L.job_id, L.id))
    by_hash: dict[str, Listing] = {}
    for listing in rows:
        by_hash.setdefault(listing.source_hash, listing)
    return sorted(by_hash.values(), key=lambda L: L.id)
