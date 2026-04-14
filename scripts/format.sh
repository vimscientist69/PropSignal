#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source .venv/bin/activate
ruff check --fix backend
black backend
npm --prefix frontend run lint -- --fix
