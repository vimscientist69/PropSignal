# PropSignal

PropSignal is a real estate deal intelligence platform that ingests listing datasets, scores opportunities, and exposes analytics through an API and dashboard.

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

## Quick Start

1. Create and activate a Python virtual environment:
   - `python3.11 -m venv .venv`
   - `source .venv/bin/activate`
2. Install backend dependencies:
   - `pip install -r backend/requirements-dev.txt`
3. Install frontend dependencies:
   - `npm --prefix frontend install`
4. Copy environment templates:
   - `cp .env.example .env`
   - `cp backend/.env.example backend/.env`
   - `cp frontend/.env.local.example frontend/.env.local`

## Local Development

- Run backend:
  - `./scripts/run-backend.sh`
- Run frontend:
  - `./scripts/run-frontend.sh`

## Quality Checks

- Lint all:
  - `./scripts/lint.sh`
- Format all:
  - `./scripts/format.sh`
- Run tests:
  - `./scripts/test.sh`

## CI

GitHub Actions workflow runs:

- backend lint, type checks, and tests
- frontend lint, type checks, and build checks
