#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--yes" ]]; then
  echo "This will DESTRUCTIVELY remove Docker Compose volumes (including Postgres data)."
  echo "Re-run with --yes to continue."
  exit 1
fi

docker compose down -v --remove-orphans
docker compose up -d postgres
docker compose run --rm backend alembic upgrade head

echo "Docker database reset complete (volumes dropped, postgres recreated, migrations applied)."
