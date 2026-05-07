# Setup Checklist

Use this checklist to verify the project is ready for development after a fresh clone.

Fully manually test commit hash: 05c439edbdc87d131caf92d8bbe8195e2b64d92b
possibly update script to use root path for `./scripts/cli-local.sh`

## Environment

- [ ] Install Node.js 20.x and npm 10+
- [ ] Install Python 3.11+ (3.11 recommended)
- [ ] Copy env templates:
  - [ ] `cp .env.example .env`
  - [ ] `cp backend/.env.example backend/.env`
  - [ ] `cp frontend/.env.local.example frontend/.env.local`

## Bootstrap

- [ ] Run `./scripts/setup.sh`
- [ ] Confirm `.venv` exists and backend/frontend dependencies are installed

## Docker Compose Baseline

- [ ] Run `./scripts/compose-up.sh -d`
- [ ] Confirm services are healthy (`postgres`, `backend`, `frontend`)
- [ ] Run migrations in container: `./scripts/migrate-docker.sh`
- [ ] (Optional, destructive) full Docker DB reset: `./scripts/reset-db-docker.sh --yes`
- [ ] Verify backend health endpoint: `http://localhost:8000/api/v1/health`
- [ ] Verify frontend placeholder page: `http://localhost:3000`

## Local Quality Gates

- [ ] Run `./scripts/lint.sh`
- [ ] Run `./scripts/test.sh`
- [ ] Run `npm --prefix frontend run build`

## Local Runtime Smoke Test

- [ ] Run backend: `./scripts/run-backend.sh`
- [ ] Run frontend: `./scripts/run-frontend.sh`
- [ ] Open `http://localhost:3000` and confirm backend status card appears
- [ ] (Optional, destructive) local DB reset: `./scripts/reset-db-local.sh --yes`

## CLI Smoke Checks

- [ ] Run `./scripts/cli-local.sh --help`
- [ ] Run `./scripts/cli-local.sh ingest data/samples/prop24_500_listings.json` (or
      `backend/tests/fixtures/propflux/valid_listings.json`) from repo root
- [ ] Run `./scripts/cli-local.sh score 1`
- [ ] Run `./scripts/cli-local.sh analyze 1`
- [ ] Run `./scripts/cli-local.sh export 1 --format json`
