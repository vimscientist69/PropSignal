#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source .venv/bin/activate
ruff check backend
black --check backend
mypy backend/app
npm --prefix frontend run lint
