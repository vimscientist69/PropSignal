# PropSignal

PropSignal is a real estate deal intelligence platform. Pre-Week-1 delivery is CLI-first with Docker
Compose orchestration, PostgreSQL persistence, and a strict PropFlux JSON ingestion contract.

## Current Scope Guardrails

- Pre-Week-1 and Week 1 focus on CLI ingestion, data normalization, scoring, and persistence.
- Frontend is intentionally placeholder-only for environment parity before Week 3.
- Supported input format is PropFlux-style JSON arrays only.
- Schema and contract are documented in `docs/data-contract-propflux.md`.

## Monorepo Layout

- `backend/` - FastAPI service and scoring pipeline code
- `frontend/` - Next.js dashboard
- `config/` - shared runtime configuration (for example scoring weights)
- `docs/` - project and contributor documentation
- `scripts/` - local developer automation helpers
- `data/` - local input data (gitignored except placeholders)
- `output/` - generated exports and artifacts (gitignored)

## Prerequisites

- Python `3.11.x`
- Node.js `20.x` (LTS)
- npm `10+`
- Docker + Docker Compose plugin

## Quick Start

1. Copy environment templates:
   - `cp .env.example .env`
   - `cp backend/.env.example backend/.env`
   - `cp frontend/.env.local.example frontend/.env.local`
2. Install local dependencies:
   - `./scripts/setup.sh`

## Docker Compose Workflow (Recommended)

- Start full stack:
  - `./scripts/compose-up.sh`
- Stop stack:
  - `./scripts/compose-down.sh`
- Stream logs:
  - `./scripts/compose-logs.sh`
- Apply migrations in container:
  - `./scripts/migrate-docker.sh`

Services:

- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`
- postgres: `localhost:5432`

## Local Development

- Run backend:
  - `./scripts/run-backend.sh`
- Run frontend:
  - `./scripts/run-frontend.sh`
- Apply migrations locally:
  - `./scripts/migrate.sh`

## CLI Workflow

- Local CLI:
  - `./scripts/cli-local.sh --help`
- Docker CLI:
  - `./scripts/cli-docker.sh --help`

Core commands:

- `ingest <path>`
- `score <job-id>`
- `analyze <job-id>`
- `export <job-id> --format json|csv`

## Quality Checks

- Lint all:
  - `./scripts/lint.sh`
- Format all:
  - `./scripts/format.sh`
- Run tests:
  - `./scripts/test.sh`

## CI

GitHub Actions workflow runs:

- backend lint, type checks, migrations, and tests
- frontend lint, type checks, and build checks
