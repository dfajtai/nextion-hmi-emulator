#!/usr/bin/env bash
# Runs nextion_parser (sets up the venv on the first run).
#   ./scripts/run.sh all path/to/FILE.HMI            everything into output/<name>/
#   ./scripts/run.sh serve output/<name>             helper server (auto-loads/saves scenarios)
#   ./scripts/run.sh --test                          test suite
#   ./scripts/run.sh --help
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
VENV="${NEXTION_VENV:-$ROOT/.venv}"
"$HERE/setup.sh" --quiet
export PYTHONPATH="$ROOT/code${PYTHONPATH:+:$PYTHONPATH}"
if [ "${1:-}" = "--test" ]; then
  cd "$ROOT/code" && exec "$VENV/bin/python" -m pytest -q tests "${@:2}"
fi
exec "$VENV/bin/python" -m nextion_parser "$@"
