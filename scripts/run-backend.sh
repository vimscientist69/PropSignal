#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port "${PORT:-8000}"
