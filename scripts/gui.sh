#!/usr/bin/env bash
# Opens the generator window (PySide6). Optional argument: a .HMI file to preselect.
#   ./scripts/gui.sh [FILE.HMI]
# It looks for PySide6 in this order and only installs when it finds none:
#   1. the project's private venv   2. the system Python ($PYTHON, default python3)   3. install into the private venv
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
VENV="${NEXTION_VENV:-$ROOT/.venv}"
PY="${PYTHON:-python3}"
has_pyside() { { [ -x "$1" ] || command -v "$1" >/dev/null 2>&1; } && "$1" -c "import PySide6.QtUiTools" >/dev/null 2>&1; }

if has_pyside "$VENV/bin/python"; then
  PYX="$VENV/bin/python"
elif has_pyside "$PY"; then
  PYX="$PY"
  echo ">> using PySide6 from the system Python ($(command -v "$PY"))"
else
  if ! command -v "$PY" >/dev/null 2>&1; then
    echo "Python 3 not found (looked for '$PY'). Install Python 3.9+ and retry." >&2
    exit 1
  fi
  echo "PySide6 (~80 MB) is not installed."
  if [ -t 0 ]; then
    read -r -p "Install it into the project's private venv ($VENV)? [Y/n] " ans
    case "$ans" in [nN]*) echo "Aborted. Alternative: pip install PySide6-Essentials"; exit 1;; esac
  fi
  "$HERE/setup.sh" --gui || { echo "Installation failed (no internet?). Install manually: pip install PySide6-Essentials" >&2; exit 1; }
  PYX="$VENV/bin/python"
fi
export PYTHONPATH="$ROOT/code${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYX" -m nextion_parser gui "$@"
