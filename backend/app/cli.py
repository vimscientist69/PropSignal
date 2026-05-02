import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from app.db.session import SessionLocal
from app.schemas.ranking import RankingQueryRequest, StrategyPreset
from app.services.analytics import run_analytics_job
from app.services.dataset_validation import run_dataset_validation
from app.services.exporting import export_job_results
from app.services.ingestion import ingest_propflux_file
from app.services.performance_baseline import run_performance_baseline
from app.services.ranking_query import (
    get_listing_detail,
    list_profiles,
    resolve_profile,
    run_ranking_query,
)
from app.services.scoring import run_scoring_job
from app.services.scoring_evaluation import run_scoring_evaluation

app = typer.Typer(help="PropSignal CLI (pre-Week-1).")


@app.command()
def ingest(path: str) -> None:
    input_path = Path(path)
    with SessionLocal() as db:
        job = ingest_propflux_file(db, input_path)
    typer.echo(f"Ingestion completed. job_id={job.id}, status={job.status}")
    typer.echo(
        "records_total="
        f"{job.records_total}, "
        f"records_valid={job.records_valid}, "
        f"records_invalid={job.records_invalid}"
    )


@app.command()
def score(job_id: int) -> None:
    with SessionLocal() as db:
        job = run_scoring_job(db, job_id)
    typer.echo(f"Scoring completed for job: {job.id}")


@app.command()
def analyze(job_id: int) -> None:
    with SessionLocal() as db:
        job = run_analytics_job(db, job_id)
    typer.echo(f"Analytics completed for job: {job.id}")


@app.command()
def export(job_id: int, format: str = typer.Option("json", "--format")) -> None:
    if format not in {"json", "csv"}:
        raise typer.BadParameter("Supported formats: json, csv")
    with SessionLocal() as db:
        output_path = export_job_results(db, job_id, format)
    typer.echo(f"Export written to: {output_path}")


@app.command("validate-dataset")
def validate_dataset(job_id: int) -> None:
    with SessionLocal() as db:
        result = run_dataset_validation(db, job_id)
    typer.echo(
        f"Dataset validation completed for job: {result.job_id}, status={result.status}, "
        f"valid_rate={result.valid_rate}, invalid_rate={result.invalid_rate}"
    )
    typer.echo(f"Report written to: {result.report_path}")


@app.command("evaluate-scoring")
def evaluate_scoring(
    job_id: int,
    reference_job_id: int | None = typer.Option(None, "--reference-job-id"),
    top_n: int = typer.Option(20, "--top-n"),
) -> None:
    with SessionLocal() as db:
        report = run_scoring_evaluation(
            db,
            job_id=job_id,
            reference_job_id=reference_job_id,
            top_n=top_n,
        )
    typer.echo(
        "Scoring evaluation completed for "
        f"job={job_id}, decision={report['decision']}, "
        f"failed_gates={','.join(report['failed_gates']) or 'none'}"
    )
    typer.echo(f"Report written to: {report['report_path']}")


@app.command("benchmark-baseline")
def benchmark_baseline(
    dataset: Annotated[list[str], typer.Option("--dataset")],
    top_n: Annotated[int, typer.Option("--top-n")] = 20,
    output_dir: Annotated[str | None, typer.Option("--output-dir")] = None,
) -> None:
    with SessionLocal() as db:
        metrics = run_performance_baseline(
            db,
            dataset_paths=dataset,
            top_n=top_n,
            output_dir=output_dir,
        )
    typer.echo(
        "Performance baseline completed for "
        f"{len(dataset)} dataset(s). "
        f"met={len(metrics['slo_assessment']['met'])}, "
        f"missed={len(metrics['slo_assessment']['missed'])}, "
        f"deferred={len(metrics['slo_assessment']['deferred'])}"
    )
    typer.echo(f"Metrics written to: {metrics['metrics_path']}")
    typer.echo(f"Summary written to: {metrics['summary_path']}")


def _parse_weight_overrides(values: list[str]) -> dict[str, float]:
    parsed: dict[str, float] = {}
    for raw in values:
        key, sep, value = raw.partition("=")
        if not sep or not key.strip():
            raise typer.BadParameter(
                f"Invalid --weight-override '{raw}'. Expected key=value format."
            )
        try:
            parsed[key.strip()] = float(value)
        except ValueError as exc:
            raise typer.BadParameter(
                f"Invalid override value in '{raw}'. Expected numeric value."
            ) from exc
    return parsed


def _emit_json_payload(payload: dict, output_json: str | None, *, pretty: bool = False) -> None:
    content = json.dumps(payload, indent=2 if pretty else None)
    typer.echo(content)
    if output_json:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        typer.echo(f"JSON written to: {output_path}")


@app.command("rank-query")
def rank_query(
    dataset_source: Annotated[list[str], typer.Option("--dataset-source")],
    strategy_preset: Annotated[StrategyPreset, typer.Option("--strategy-preset")],
    province: Annotated[str | None, typer.Option("--province")] = None,
    city: Annotated[str | None, typer.Option("--city")] = None,
    suburb: Annotated[str | None, typer.Option("--suburb")] = None,
    price_min: Annotated[float | None, typer.Option("--price-min")] = None,
    price_max: Annotated[float | None, typer.Option("--price-max")] = None,
    property_type: Annotated[str | None, typer.Option("--property-type")] = None,
    bedrooms_min: Annotated[int | None, typer.Option("--bedrooms-min")] = None,
    bathrooms_min: Annotated[float | None, typer.Option("--bathrooms-min")] = None,
    confidence_min: Annotated[float | None, typer.Option("--confidence-min")] = None,
    top_n: Annotated[int | None, typer.Option("--top-n")] = None,
    page: Annotated[int | None, typer.Option("--page")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size")] = None,
    weight_override: Annotated[list[str] | None, typer.Option("--weight-override")] = None,
    output_json: Annotated[str | None, typer.Option("--output-json")] = None,
) -> None:
    request_payload = {
        "dataset_sources": dataset_source,
        "filters": {
            "province": province,
            "city": city,
            "suburb": suburb,
            "price_min": price_min,
            "price_max": price_max,
            "property_type": property_type,
            "bedrooms_min": bedrooms_min,
            "bathrooms_min": bathrooms_min,
            "confidence_min": confidence_min,
        },
        "strategy": {
            "preset": strategy_preset,
            "weight_overrides": _parse_weight_overrides(weight_override or []),
        },
        "result_window": {"top_n": top_n, "page": page, "page_size": page_size},
        "sort_mode": "score_desc",
    }
    try:
        request = RankingQueryRequest.model_validate(request_payload)
        with SessionLocal() as db:
            response = run_ranking_query(request, db=db)
    except ValidationError as exc:
        raise typer.BadParameter(exc.json()) from exc
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    payload = response.model_dump(mode="json")
    typer.echo(
        "Ranking completed: "
        f"run_id={response.run_id}, "
        f"results={len(response.results)}, "
        f"profile_id={response.resolved_profile.profile_id}"
    )
    _emit_json_payload(payload, output_json)


@app.command("listing-detail")
def listing_detail(
    run_id: Annotated[str, typer.Option("--run-id")],
    listing_id: Annotated[int, typer.Option("--listing-id")],
    pretty: Annotated[bool, typer.Option("--pretty")] = False,
) -> None:
    response = get_listing_detail(run_id, listing_id)
    typer.echo(f"Listing detail loaded: run_id={run_id}, listing_id={listing_id}")
    _emit_json_payload(response.model_dump(mode="json"), output_json=None, pretty=pretty)


@app.command("profiles-list")
def profiles_list() -> None:
    profiles = list_profiles()
    typer.echo(f"Profiles available: {len(profiles)}")
    _emit_json_payload(
        {"profiles": [profile.model_dump(mode="json") for profile in profiles]},
        output_json=None,
    )


@app.command("profile-show")
def profile_show(
    preset: Annotated[StrategyPreset, typer.Option("--preset")],
    pretty: Annotated[bool, typer.Option("--pretty")] = False,
) -> None:
    response = resolve_profile(preset)
    typer.echo(f"Profile resolved: preset={preset.value}, profile_id={response.profile_id}")
    _emit_json_payload(response.model_dump(mode="json"), output_json=None, pretty=pretty)


if __name__ == "__main__":
    app()
