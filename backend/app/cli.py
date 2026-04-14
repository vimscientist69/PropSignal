from pathlib import Path

import typer

from app.db.session import SessionLocal
from app.services.analytics import run_analytics_job
from app.services.exporting import export_job_results
from app.services.ingestion import ingest_propflux_file
from app.services.scoring import run_scoring_job

app = typer.Typer(help="PropSignal CLI (pre-Week-1).")


@app.command()
def ingest(path: str) -> None:
    input_path = Path(path)
    with SessionLocal() as db:
        job = ingest_propflux_file(db, input_path)
    typer.echo(f"Ingestion completed. job_id={job.id}")
    typer.echo("records_total=" f"{job.records_total}, records_valid={job.records_valid}")


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


if __name__ == "__main__":
    app()
