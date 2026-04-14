#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d ".venv" ]]; then
  if command -v python3.11 >/dev/null 2>&1; then
    python3.11 -m venv .venv
  else
    python3 -m venv .venv
  fi
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements-dev.txt
npm --prefix frontend install

echo "Setup complete."
