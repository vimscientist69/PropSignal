# Setup Checklist

Verify a fresh clone before demoing or developing. Run commands from **repository root**.

## Environment

- [ ] Node.js 20.x and npm 10+
- [ ] Python 3.11.x
- [ ] Docker + Docker Compose (recommended)
- [ ] Copy env templates:
  - [ ] `cp .env.example .env`
  - [ ] `cp backend/.env.example backend/.env`
  - [ ] `cp frontend/.env.local.example frontend/.env.local`

## Bootstrap

- [ ] `./scripts/setup.sh`
- [ ] `.venv` exists; backend and frontend dependencies installed

## Docker Compose (recommended)

- [ ] `./scripts/compose-up.sh -d`
- [ ] Services healthy: `postgres`, `backend`, `frontend`
- [ ] `./scripts/migrate-docker.sh`
- [ ] Backend health: `http://localhost:8000/api/v1/health`
- [ ] Dashboard: `http://localhost:3000/dashboard/control`

## Local quality gates

- [ ] `./scripts/lint.sh`
- [ ] `./scripts/test.sh`
- [ ] `npm --prefix frontend run build`

## Demo seed (optional)

- [ ] Postgres reachable (compose or local)
- [ ] `./scripts/reset-db-local.sh --yes` (optional, clean `job_id=1`)
- [ ] `./scripts/demo-local.sh`
- [ ] Two terminals: `./scripts/run-backend.sh` and `./scripts/run-frontend.sh` (if not using compose API/frontend)
- [ ] Control Panel shows source `job:1`; Runs tab lists at least one run

## CLI smoke

- [ ] `./scripts/cli-local.sh --help`
- [ ] `./scripts/cli-local.sh profiles-list`
- [ ] `./scripts/cli-local.sh rank-query --dataset-source job:1 --strategy-preset rental_income --top-n 3` (after demo seed)

## Destructive resets (when needed)

- [ ] Docker DB: `./scripts/reset-db-docker.sh --yes`
- [ ] Local DB: `./scripts/reset-db-local.sh --yes`
