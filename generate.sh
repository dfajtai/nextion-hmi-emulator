#!/usr/bin/env bash
# Put your .HMI file(s) next to this script and run it (double-click or ./generate.sh).
# Everything is generated into output/<name>/ and the launcher page opens. First run creates the Python environment by itself.
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
exec ./scripts/run.sh "$@"
