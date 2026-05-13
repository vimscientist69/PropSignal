#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--yes" ]]; then
  echo "This will DESTRUCTIVELY reset the local database schema and data."
  echo "Re-run with --yes to continue."
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

cd backend
alembic downgrade base
alembic upgrade head

echo "Local database reset complete (downgrade base -> upgrade head)."
