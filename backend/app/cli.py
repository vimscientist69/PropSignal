from pathlib import Path
from typing import Annotated

import typer

from app.db.session import SessionLocal
from app.services.analytics import run_analytics_job
from app.services.dataset_validation import run_dataset_validation
from app.services.exporting import export_job_results
from app.services.ingestion import ingest_propflux_file
from app.services.performance_baseline import run_performance_baseline
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


if __name__ == "__main__":
    app()
