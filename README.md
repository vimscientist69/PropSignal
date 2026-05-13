# PropSignal

PropSignal ingests property listing datasets, scores them against configurable investment strategies, and surfaces ranked shortlists with explainable diagnostics. The platform is built for operators who need repeatable deal triage—not one-off spreadsheet sorts.

**Core value**

- **Ingest once, rank many times** — normalized listings persist in PostgreSQL; ranking runs are reproducible and auditable.
- **Strategy-driven scoring** — presets (rental income, resale arbitrage, etc.) map to weighted signal profiles you can tune per run.
- **CLI and dashboard parity** — the same backend contracts power terminal workflows and the web control center.
- **Explainability by default** — each score carries signal breakdowns, comp context, and ROI assumptions where applicable.

## Who this is for

Developers and analysts working South African (and similar) residential listing feeds in **PropFlux-style JSON** (another project of mine - a scraping system). PropSignal is not a consumer property portal; it is an internal scoring and ranking pipeline with operator tooling.

## Repository layout

| Path | Role |
|------|------|
| `backend/` | FastAPI service, scoring engine, CLI (`app/cli.py`), Alembic migrations |
| `frontend/` | Next.js dashboard at `/dashboard/*` |
| `config/` | Shared scoring weights and evaluation thresholds (`scoring.yaml`) |
| `backend/config/` | Strategy profile definitions (`scoring_profiles.yaml`) |
| `docs/` | Setup, configuration glossary, dashboard guide, contracts |
| `scripts/` | Compose, migrate, lint, test, and CLI wrappers (run from repo root) |
| `data/` | Local inputs (gitignored except samples) |
| `output/` | CLI exports and evaluation artifacts (gitignored) |

## Prerequisites

- Python **3.11.x**
- Node.js **20.x** (LTS) and npm **10+**
- Docker + Docker Compose plugin (recommended for full stack)

## Quick start

1. Copy environment templates:

   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   cp frontend/.env.local.example frontend/.env.local
   ```

2. Install dependencies:

   ```bash
   ./scripts/setup.sh
   ```

3. Start the stack (Postgres, API, dashboard):

   ```bash
   ./scripts/compose-up.sh
   ./scripts/migrate-docker.sh
   ```

4. Open:

   - Dashboard: [http://localhost:3000/dashboard/control](http://localhost:3000/dashboard/control)
   - API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

For a step-by-step verification list, see [`docs/setup-checklist.md`](docs/setup-checklist.md).

## Development workflows

### Docker Compose (recommended)

| Task | Command |
|------|---------|
| Start stack | `./scripts/compose-up.sh` |
| Stop stack | `./scripts/compose-down.sh` |
| Logs | `./scripts/compose-logs.sh` |
| Migrations | `./scripts/migrate-docker.sh` |
| CLI in container | `./scripts/cli-docker.sh --help` |
| Reset DB (destructive) | `./scripts/reset-db-docker.sh --yes` |

Default ports: frontend **3000**, backend **8000**, Postgres **5432**.

### Local processes

| Task | Command |
|------|---------|
| API only | `./scripts/run-backend.sh` |
| Frontend only | `./scripts/run-frontend.sh` |
| Migrations | `./scripts/migrate.sh` |
| CLI | `./scripts/cli-local.sh --help` |
| Reset DB (destructive) | `./scripts/reset-db-local.sh --yes` |

### Typical data path

1. **Ingest** a PropFlux JSON array → creates an `ingestion_job` and normalized `listings`.
2. **Score** the job (batch scoring into `score_results`).
3. **Rank** via API/CLI/dashboard — strategy preset + filters + result window → persisted `ranking_run`.
4. **Inspect** listing detail, export CSV/JSON, or compare runs in the dashboard.

CLI reference: [`docs/cli-usage.md`](docs/cli-usage.md).  
Data contract: [`docs/data-contract-propflux.md`](docs/data-contract-propflux.md).

## Quality gates

Before opening a PR:

```bash
./scripts/lint.sh
./scripts/test.sh
npm --prefix frontend run build   # when frontend changes
```

CI runs backend lint/type/tests/migrations and frontend lint/type/build.

## Documentation

| Document | Contents |
|----------|----------|
| [`docs/README.md`](docs/README.md) | Documentation index |
| [`docs/configuration.md`](docs/configuration.md) | Environment variables, config files, and term definitions |
| [`docs/dashboard.md`](docs/dashboard.md) | Dashboard tabs: purpose, workflows, and behavior |
| [`docs/setup-checklist.md`](docs/setup-checklist.md) | Fresh-clone verification |
| [`docs/cli-usage.md`](docs/cli-usage.md) | CLI commands and job lifecycle |
| [`docs/data-contract-propflux.md`](docs/data-contract-propflux.md) | Ingestion JSON schema |
| [`docs/dashboard-frontend-test-spec.md`](docs/dashboard-frontend-test-spec.md) | Manual QA checklist for the UI |

Roadmap and phase history: [`.cursor/rules/PROJECT_NOTE.md`](.cursor/rules/PROJECT_NOTE.md).  
Current completion snapshot: [`docs/current-project-status.md`](docs/current-project-status.md).

## Supported input

PropFlux-style **JSON arrays** of listing objects only. Partial-accept ingestion stores valid rows and rejects invalid ones with diagnostics. See the data contract doc for required and optional fields.
