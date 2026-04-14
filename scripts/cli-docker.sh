#!/usr/bin/env bash
set -euo pipefail

docker compose run --rm backend python -m app.cli "$@"
