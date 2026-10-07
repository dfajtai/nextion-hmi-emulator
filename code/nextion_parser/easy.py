"""Easy mode: one file, no options.

Put the generator (``nextion-generator.pyz``) next to one or more ``.HMI`` files and run it (double-click, or
``python3 nextion-generator.pyz``). For every ``.HMI`` beside it, everything is generated into ``output/<name>/`` and the
launcher page opens in the browser. A ``scenarios/`` folder next to the HMI (optional) is used as the source of
``variables.json`` / ``csv_profiles.json`` / scenarios.

With command-line arguments it behaves exactly like the normal command line (``cli.main``); ``gui`` opens the Qt window
(``builder_gui``).
"""
from __future__ import annotations

import os
import sys
import traceback
import webbrowser
from pathlib import Path

from . import cli


def base_dir() -> Path:
    """The folder of the .pyz (or the current folder when run as a module)."""
    arg0 = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else Path.cwd()
    return arg0.parent if arg0.is_file() and arg0.suffix.lower() in (".pyz", ".pyzw") else Path.cwd()


def find_hmi(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".hmi")


def _pause(interactive: bool) -> None:
    """Keep the window open until a key is pressed (not when a wrapper script does that itself: NX_NO_PAUSE)."""
    if interactive and not os.environ.get("NX_NO_PAUSE"):
        try:
            input("\nPress Enter to close...")
        except EOFError:
            pass


def easy(folder: Path | None = None, files: list[Path] | None = None) -> int:
    """Process every .HMI in `folder` (default: next to the .pyz / the current folder), or the explicitly given `files`."""
    folder = folder or (Path.cwd() if files else base_dir())
    interactive = sys.stdout.isatty()           # double-clicked / run in a terminal: open the browser and keep the window
    hmis = files if files else find_hmi(folder)
    if not hmis:
        print(f"No .HMI file found in {folder}\nPut your .HMI file next to this file and run it again.", file=sys.stderr)
        _pause(interactive)
        return 2
    rc, launchers = 0, []
    for hmi in hmis:
        out = folder / "output" / hmi.stem
        print(f"\n=== {hmi.name} -> {out}")
        try:
            r = cli.main(["all", str(hmi), "-o", str(out)])
        except SystemExit as e:                                  # argparse and friends
            r = int(e.code or 1)
        except Exception as e:                                   # a bug must not close the window without a word
            print(f"\nUNEXPECTED ERROR while processing {hmi.name}: {type(e).__name__}: {e}", file=sys.stderr)
            traceback.print_exc()
            r = 1
        rc = rc or r
        if (out / "index.html").is_file():
            launchers.append(out / "index.html")
    if launchers:
        print(f"\nDone. Open: {launchers[0]}" + (f"  (+{len(launchers) - 1} more)" if len(launchers) > 1 else ""))
        if interactive:
            webbrowser.open(launchers[0].as_uri())
    if rc not in (0, 4) and not os.environ.get("NX_NO_PAUSE"):     # (generate.sh/.bat print their own message)
        print("\nSomething went wrong - see the messages above.", file=sys.stderr)
    if rc == 4:
        print("Note: some scenarios do not match this HMI (see the messages above); everything was generated anyway.")
    _pause(interactive)
    return rc


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "gui":
        try:
            from .builder_gui.app import main as gui_main
        except ImportError as e:                       # the GUI is optional: PySide6 is not part of the standard library
            print(f"The GUI needs PySide6 ({e}).  Install it with: pip install -r code/requirements-gui.txt  (scripts/gui.sh does it)",
                  file=sys.stderr)
            return 2
        return gui_main(argv[1:])
    if argv and all(a.lower().endswith(".hmi") for a in argv):      # `generate.sh my.HMI` / `nextion-generator.pyz my.HMI`
        missing = [a for a in argv if not Path(a).is_file()]
        if missing:
            print(f"Not found: {', '.join(missing)}", file=sys.stderr)
            return 2
        return easy(files=[Path(a) for a in argv])
    return cli.main(argv) if argv else easy()


def run() -> None:
    """Entry point of the .pyz (zipapp ignores the return value of ``main``)."""
    sys.exit(main())
