#!/usr/bin/env bash
# Seed a minimal local dataset for portfolio demo / interviewer walkthrough.
# Prerequisites: .venv, backend/.env, Postgres reachable (local or compose).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FIXTURE="${ROOT_DIR}/backend/tests/fixtures/propflux/valid_listings.json"

if [[ ! -f "$FIXTURE" ]]; then
  echo "Fixture not found: $FIXTURE" >&2
  exit 1
fi

echo "==> Applying migrations"
./scripts/migrate.sh

echo "==> Ingesting fixture: backend/tests/fixtures/propflux/valid_listings.json"
./scripts/cli-local.sh ingest "$FIXTURE"

echo "==> Scoring job 1"
./scripts/cli-local.sh score 1

echo "==> Validating dataset"
./scripts/cli-local.sh validate-dataset 1

echo "==> Ranking (rental_income preset, top 5)"
./scripts/cli-local.sh rank-query \
  --dataset-source job:1 \
  --strategy-preset rental_income \
  --top-n 5

cat <<'EOF'

Demo data is ready.

Next (two terminals):
  ./scripts/run-backend.sh
  ./scripts/run-frontend.sh

Then open:
  http://localhost:3000/dashboard/control
  http://localhost:3000/dashboard/runs   (compare two runs after a second rank-query)

Tip: for a clean job_id=1, run ./scripts/reset-db-local.sh --yes before this script.

Full walkthrough: docs/demo.md
EOF
