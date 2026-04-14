#!/usr/bin/env bash
set -euo pipefail

docker compose run --rm backend alembic upgrade head
