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
- CLI ingestion currently enforces PropFlux JSON array contract.

## Scoring Configuration

The initial scoring profile lives at `config/scoring.yaml`.

- `weights` controls contribution by signal.
- `rules` controls baseline thresholds.
- `flags` enables or disables optional signals.
