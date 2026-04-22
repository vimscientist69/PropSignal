from __future__ import annotations

from app.models.ingestion_job import IngestionJob
from app.models.listing import Listing
from app.models.raw_listing import RawListing
from app.models.score_result import ScoreResult
from app.services.scoring_evaluation import run_scoring_evaluation
from sqlalchemy.orm import Session


def _build_explanation(normalized_value: float, final_score: float) -> dict[str, object]:
    score_a = round(normalized_value, 6)
    score_b = round(normalized_value, 6)
    weight_a = 0.5
    weight_b = 0.5
    contribution_a = round(score_a * weight_a, 6)
    contribution_b = round(score_b * weight_b, 6)
    weighted_sum = round(contribution_a + contribution_b, 6)
    return {
        "signals": [
            {
                "name": "price_vs_comp",
                "normalized_score": score_a,
                "weight": weight_a,
                "weighted_contribution": contribution_a,
            },
            {
                "name": "roi_proxy",
                "normalized_score": score_b,
                "weight": weight_b,
                "weighted_contribution": contribution_b,
            },
        ],
        "score_math": {
            "weighted_sum_0_to_1": weighted_sum,
            "final_score_0_to_100": round(final_score, 2),
        },
    }


def _seed_scored_job(
    db_session: Session,
    *,
    sample_size: int,
    score_order_desc: bool,
) -> IngestionJob:
    job = IngestionJob(
        input_path=f"fixture-{sample_size}.json",
        status="completed",
        records_total=sample_size,
        records_valid=sample_size,
        records_invalid=0,
    )
    db_session.add(job)
    db_session.flush()

    for index in range(sample_size):
        listing = Listing(
            job_id=job.id,
            source_hash=f"job-{job.id}-hash-{index}",
            title=f"Listing {index}",
            price=float(1_000_000 + index * 500),
            location="Cape Town",
            bedrooms=3,
            bathrooms=2.0,
            property_type="house",
            description="Fixture listing",
            listing_id=f"LIST-{index}",
            source_site=f"propflux-job-{job.id}",
            city="Cape Town",
            province="Western Cape",
            floor_size=100.0,
            normalized_payload={"fixture": True},
        )
        db_session.add(listing)
        db_session.flush()

        db_session.add(
            RawListing(
                job_id=job.id,
                record_index=index,
                source_site=f"propflux-job-{job.id}",
                listing_id=listing.listing_id,
                payload={"price": listing.price},
            )
        )

        rank_value = sample_size - index if score_order_desc else index + 1
        normalized_value = round(rank_value / (sample_size + 1), 6)
        final_score = round(normalized_value * 100.0, 2)
        db_session.add(
            ScoreResult(
                job_id=job.id,
                listing_id=listing.id,
                score=final_score,
                confidence=0.9,
                deal_reason="fixture",
                explanation=_build_explanation(normalized_value, final_score),
                model_version="advanced_v2",
            )
        )

    db_session.commit()
    db_session.refresh(job)
    return job


def test_scoring_evaluation_promotes_when_all_gates_pass(db_session: Session) -> None:
    current_job = _seed_scored_job(db_session, sample_size=120, score_order_desc=True)
    reference_job = _seed_scored_job(db_session, sample_size=120, score_order_desc=True)

    report = run_scoring_evaluation(
        db_session,
        job_id=current_job.id,
        reference_job_id=reference_job.id,
        top_n=20,
    )

    assert report["decision"] == "promote"
    assert report["failed_gates"] == []
    assert report["warning_gates"] == []
    assert report["gates"]["stability"]["status"] == "pass"


def test_scoring_evaluation_reverts_when_stability_fails(db_session: Session) -> None:
    current_job = _seed_scored_job(db_session, sample_size=120, score_order_desc=True)
    reversed_reference = _seed_scored_job(db_session, sample_size=120, score_order_desc=False)

    report = run_scoring_evaluation(
        db_session,
        job_id=current_job.id,
        reference_job_id=reversed_reference.id,
        top_n=20,
    )

    assert report["decision"] == "revert"
    assert "stability" in report["failed_gates"]


def test_scoring_evaluation_marks_experimental_when_sample_too_small(
    db_session: Session,
) -> None:
    current_job = _seed_scored_job(db_session, sample_size=40, score_order_desc=True)
    reference_job = _seed_scored_job(db_session, sample_size=40, score_order_desc=True)

    report = run_scoring_evaluation(
        db_session,
        job_id=current_job.id,
        reference_job_id=reference_job.id,
        top_n=20,
    )

    assert report["decision"] == "experimental"
    assert "sample_size" in report["warning_gates"]
