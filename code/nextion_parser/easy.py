"""Easy mode: one file, no options.

Put the generator (``nextion-generator.pyz``) next to one or more ``.HMI`` files and run it (double-click, or
``python3 nextion-generator.pyz``). For every ``.HMI`` beside it, everything is generated into ``output/<name>/`` and the
launcher page opens in the browser. A ``scenarios/`` folder next to the HMI (optional) is used as the source of
``variables.json`` / ``csv_profiles.json`` / scenarios.

With command-line arguments it behaves exactly like the normal command line (``cli.main``); ``gui`` opens the Qt window
(``builder_gui``).
"""
from __future__ import annotations

import sys
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
    if interactive:
        try:
            input("\nPress Enter to close...")
        except EOFError:
            pass


def easy(folder: Path | None = None) -> int:
    folder = folder or base_dir()
    interactive = sys.stdout.isatty()           # double-clicked / run in a terminal: open the browser and keep the window
    hmis = find_hmi(folder)
    if not hmis:
        print(f"No .HMI file found in {folder}\nPut your .HMI file next to this file and run it again.", file=sys.stderr)
        _pause(interactive)
        return 2
    rc, launchers = 0, []
    for hmi in hmis:
        out = folder / "output" / hmi.stem
        print(f"\n=== {hmi.name} -> {out}")
        r = cli.main(["all", str(hmi), "-o", str(out)])
        rc = rc or r
        if (out / "index.html").is_file():
            launchers.append(out / "index.html")
    if launchers:
        print(f"\nDone. Open: {launchers[0]}" + (f"  (+{len(launchers) - 1} more)" if len(launchers) > 1 else ""))
        if interactive:
            webbrowser.open(launchers[0].as_uri())
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
    return cli.main(argv) if argv else easy()


def run() -> None:
    """Entry point of the .pyz (zipapp ignores the return value of ``main``)."""
    sys.exit(main())
