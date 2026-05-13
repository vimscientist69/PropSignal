#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
source "$ROOT_DIR/.venv/bin/activate"

# Allow ingest paths relative to repo root (e.g. data/samples/...).
if [[ "${1:-}" == "ingest" && -n "${2:-}" ]]; then
  if [[ "$2" != /* ]]; then
    set -- "$1" "$ROOT_DIR/$2" "${@:3}"
  fi
fi

cd "$ROOT_DIR/backend"
python -m app.cli "$@"
