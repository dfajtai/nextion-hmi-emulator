#!/usr/bin/env bash
# Builds the single-file "easy generator": dist/nextion-generator.pyz (needs only Python 3.9+ on the user's machine).
# Give the user this one file; they put it next to their .HMI file and double-click it.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
PY="${PYTHON:-python3}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -r "$ROOT/code/nextion_parser" "$STAGE/nextion_parser"
find "$STAGE" -name __pycache__ -type d -prune -exec rm -rf {} +
mkdir -p "$ROOT/dist"
"$PY" -m zipapp "$STAGE" -o "$ROOT/dist/nextion-generator.pyz" -p "/usr/bin/env python3" -m "nextion_parser.easy:run"
echo "built: $ROOT/dist/nextion-generator.pyz"
