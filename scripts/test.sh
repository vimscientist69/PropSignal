#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source .venv/bin/activate
pytest backend/tests
npm --prefix frontend run typecheck
