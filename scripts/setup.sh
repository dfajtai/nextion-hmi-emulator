#!/usr/bin/env bash
# One-time (idempotent) environment setup: creates the private venv and installs code/requirements.txt.
# `--gui` also installs the optional window dependency (PySide6). Safe to run any number of times; run.sh calls it automatically. Override the venv location with NEXTION_VENV
# (a local disk is faster than a network drive) and the interpreter with PYTHON.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
VENV="${NEXTION_VENV:-$ROOT/.venv}"
PY="${PYTHON:-python3}"
QUIET=""; GUI=""
for a in "$@"; do case "$a" in --quiet) QUIET="--quiet";; --gui) GUI=1;; esac; done

say() { [ "$QUIET" = "--quiet" ] || echo "$@"; }

command -v "$PY" >/dev/null 2>&1 || { echo "Python 3 not found (looked for '$PY'). Install Python 3.9+ and retry." >&2; exit 1; }

if [ ! -f "$VENV/bin/activate" ]; then
  say ">> creating venv: $VENV"
  "$PY" -m venv "$VENV" 2>/dev/null || "$PY" -m venv --copies "$VENV"   # symlinks may fail on a network file system
fi

STAMP="$VENV/.requirements.sha"
SUM="$(sha256sum "$ROOT/code/requirements.txt" | cut -d' ' -f1)"
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$SUM" ]; then
  say ">> installing dependencies"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -r "$ROOT/code/requirements.txt"
  echo "$SUM" > "$STAMP"
fi
if [ -n "$GUI" ]; then                     # optional extras for the window (PySide6); not needed by the command line tool
  GSTAMP="$VENV/.requirements-gui.sha"
  GSUM="$(sha256sum "$ROOT/code/requirements-gui.txt" | cut -d' ' -f1)"
  if [ ! -f "$GSTAMP" ] || [ "$(cat "$GSTAMP")" != "$GSUM" ]; then
    say ">> installing GUI dependencies (PySide6)"
    "$VENV/bin/python" -m pip install --quiet -r "$ROOT/code/requirements-gui.txt"
    echo "$GSUM" > "$GSTAMP"
  fi
fi
say ">> environment ready ($VENV)"
