# Configuration Guide

## Environment Files

- Root `.env` is for shared local script values.
- `backend/.env` is for API service runtime configuration.
- `frontend/.env.local` is for browser-exposed frontend configuration.

Use the provided example files to create local copies:

- `.env.example`
- `backend/.env.example`
- `frontend/.env.local.example`

Do not commit real environment files with secrets.

## Backend Variables

- `APP_NAME` - API title shown in docs.
- `ENVIRONMENT` - runtime environment label.
- `API_PREFIX` - API route prefix.
- `FRONTEND_URL` - allowed CORS origin for local frontend.
- `DATABASE_URL` - SQLAlchemy runtime connection string.
- `ALEMBIC_DATABASE_URL` - Alembic migration connection string.

## Frontend Variables

- `NEXT_PUBLIC_API_BASE_URL` - base URL for backend API calls from the dashboard.

## Docker Compose Defaults

Compose currently provisions:

- Postgres `16` at `localhost:5432`
- backend API at `localhost:8000`
- placeholder frontend at `localhost:3000`

Default compose DB values:

- user: `propsignal`
- password: `propsignal`
- database: `propsignal`

## CLI Runtime Notes

- CLI commands run from `backend/app/cli.py`.
- Use `./scripts/cli-local.sh` for local execution.
- Use `./scripts/cli-docker.sh` for containerized execution.
- CLI ingestion enforces PropFlux JSON array contract with partial-accept processing.
- Job statuses: `created`, `processing`, `completed`, `completed_with_errors`, `failed`.

## Ingestion Persistence Layout

- `ingestion_jobs`: lifecycle and aggregate counters
- `raw_listings`: immutable raw record snapshots
- `listings`: normalized canonical records with dedup constraints
- `rejected_listings`: invalid records and validation diagnostics

## Dedup Configuration Behavior

- Primary dedup key: `source_site + listing_id` (when present).
- Fallback dedup key: computed `source_hash` from normalized payload.
- Re-ingesting duplicate records updates canonical rows in `listings`.

## Scoring Configuration

The initial scoring profile lives at `config/scoring.yaml`.

- `weights` controls contribution by signal.
- `rules` controls baseline thresholds.
- `flags` enables or disables optional signals.
