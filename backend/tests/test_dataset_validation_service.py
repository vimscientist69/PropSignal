from pathlib import Path

from app.models.dataset_validation_result import DatasetValidationResult
from app.services.dataset_validation import run_dataset_validation
from app.services.ingestion import ingest_propflux_file
from sqlalchemy import func, select
from sqlalchemy.orm import Session

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "propflux"


def test_dataset_validation_pass_for_clean_dataset(db_session: Session) -> None:
    job = ingest_propflux_file(db_session, FIXTURE_DIR / "valid_listings.json")
    result = run_dataset_validation(db_session, job.id)

    assert result.status == "pass"
    assert result.valid_rate == 1.0
    assert result.invalid_rate == 0.0
    assert result.duplicate_rate == 0.0
    assert result.price_null_rate == 0.0
    assert result.summary["counts"]["total"] == 1
    assert result.report_path != ""


def test_dataset_validation_fail_for_low_valid_rate(db_session: Session) -> None:
    job = ingest_propflux_file(db_session, FIXTURE_DIR / "mixed_valid_invalid.json")
    result = run_dataset_validation(db_session, job.id)
    assert result.status == "fail"
    assert result.valid_rate < 0.7


def test_dataset_validation_warn_for_duplicates_and_is_idempotent(db_session: Session) -> None:
    job = ingest_propflux_file(db_session, FIXTURE_DIR / "duplicate_records.json")
    first = run_dataset_validation(db_session, job.id)
    second = run_dataset_validation(db_session, job.id)

    assert first.status == "warn"
    assert second.status == "warn"
    assert first.id == second.id

    count = db_session.scalar(
        select(func.count())
        .select_from(DatasetValidationResult)
        .where(DatasetValidationResult.job_id == job.id)
    )
    assert count == 1
