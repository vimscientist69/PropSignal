from pathlib import Path
from types import SimpleNamespace

from app.cli import app
from typer.testing import CliRunner


class DummySession:
    def __enter__(self) -> "DummySession":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_cli_help_includes_preweek1_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "score" in result.stdout
    assert "analyze" in result.stdout
    assert "export" in result.stdout


def test_cli_ingest_uses_ingestion_service(monkeypatch) -> None:
    runner = CliRunner()
    temp_file = Path("backend/tests/fixtures/propflux/valid_listings.json")

    def fake_ingest_propflux_file(db, path: Path):
        assert path == temp_file
        return SimpleNamespace(
            id=42,
            status="completed",
            records_total=1,
            records_valid=1,
            records_invalid=0,
        )

    monkeypatch.setattr("app.cli.SessionLocal", DummySession)
    monkeypatch.setattr("app.cli.ingest_propflux_file", fake_ingest_propflux_file)

    result = runner.invoke(app, ["ingest", str(temp_file)])

    assert result.exit_code == 0
    assert "job_id=42" in result.stdout
    assert "records_invalid=0" in result.stdout


def test_cli_export_rejects_unsupported_format() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["export", "1", "--format", "xml"])
    assert result.exit_code == 2
