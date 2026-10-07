#!/usr/bin/env bash
# Put your .HMI file(s) next to this script and run it (double-click or ./generate.sh), or name them:
#   ./generate.sh                  every .HMI next to this script
#   ./generate.sh a.HMI b.HMI      just these files (output/<name>/ in the current folder)
# Everything is generated into output/<name>/ and the launcher page opens. The first run creates the Python environment by itself.
# The window stays open until a key is pressed, also after an error.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ "$#" -eq 0 ] && cd "$HERE"            # no arguments: work in the folder of this script (also when double-clicked)
export NX_NO_PAUSE=1                    # this script does the waiting (below)

"$HERE/scripts/run.sh" "$@"
rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 4 ]; then
  echo >&2
  echo "Something went wrong (exit code $rc) - see the messages above." >&2
fi
if [ -t 0 ] && [ -t 1 ]; then           # an interactive terminal (e.g. a double-click "run in terminal")
  echo
  read -r -n 1 -s -p "Press any key to close..."
  echo
fi
exit "$rc"
