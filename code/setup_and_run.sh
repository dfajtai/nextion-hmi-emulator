#!/usr/bin/env bash
# Creates / activates a private venv, installs the dependencies, then runs nextion_parser inside it.
#   ./setup_and_run.sh all ../sample/bioscale_research.HMI -o /tmp/out
#   ./setup_and_run.sh summary FILE.HMI
#   ./setup_and_run.sh emulator FILE.HMI --start pageMainAuto --lang en
#   ./setup_and_run.sh --test            (pytest)
# The venv lives in $NEXTION_VENV, by default <project>/.venv  (may be slower on a network drive)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
VENV="${NEXTION_VENV:-$ROOT/.venv}"
PY="${PYTHON:-python3}"

if [ ! -f "$VENV/bin/activate" ]; then
  echo ">> creating venv: $VENV"
  "$PY" -m venv "$VENV" 2>/dev/null || "$PY" -m venv --copies "$VENV"   # symlinks may fail on a network file system
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

STAMP="$VENV/.requirements.sha"
SUM="$(sha256sum "$HERE/requirements.txt" | cut -d' ' -f1)"
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$SUM" ]; then
  echo ">> installing dependencies"
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet -r "$HERE/requirements.txt"
  echo "$SUM" > "$STAMP"
fi

export PYTHONPATH="$HERE${PYTHONPATH:+:$PYTHONPATH}"
if [ "${1:-}" = "--test" ]; then
  cd "$HERE" && exec python -m pytest -q tests
fi
exec python -m nextion_parser "$@"
