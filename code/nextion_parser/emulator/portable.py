"""Files around the portable (basic) package and the output folder: scenario updater scripts, start scripts, README."""
from __future__ import annotations

from importlib import resources
from pathlib import Path

PORTABLE_README = """Scenarios folder / Forgatókönyvek mappája
==========================================
EN: Scenario .json files recorded in the expert emulator belong here. Double-click start.bat (Windows) or start.sh
    (Linux/macOS, needs Python 3): it collects the files and opens the emulator, which finds them automatically.
    To collect files from another folder (e.g. Downloads) drag that folder onto update_scenarios.bat, or run
    `python3 update_scenarios.py <folder>`; then reload index.html. Files other than scenario .json are ignored.
HU: Az expert emulátorban rögzített forgatókönyv .json fájlok ide valók. Kattints duplán a start.bat-ra (Windows) vagy
    start.sh-ra (Linux/macOS, Python 3 kell): összegyűjti a fájlokat és megnyitja az emulátort, ami magától megtalálja őket.
    Másik mappából (pl. Letöltések) úgy gyűjthetsz, hogy a mappát ráhúzod az update_scenarios.bat-ra, vagy:
    `python3 update_scenarios.py <mappa>`; utána töltsd újra az index.html-t.
"""


def add_updater(folder: Path, start_scripts: bool = False) -> None:
    """Copy update_scenarios.py + double-click wrappers into `folder` (and, for a package, start.bat/start.sh)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    src = resources.files("nextion_parser.emulator").joinpath("update_scenarios.py").read_text(encoding="utf-8")
    (folder / "update_scenarios.py").write_text(src, encoding="utf-8")
    (folder / "update_scenarios.bat").write_bytes(
        b'@echo off\r\npy -3 "%~dp0update_scenarios.py" %* || python "%~dp0update_scenarios.py" %*\r\npause\r\n')
    sh = folder / "update_scenarios.sh"
    sh.write_text('#!/bin/sh\ncd "$(dirname "$0")" && python3 update_scenarios.py "$@"\n', encoding="utf-8")
    sh.chmod(0o755)
    if start_scripts:                       # one double-click: refresh scenarios.js, then open the emulator from disk
        (folder / "start.bat").write_bytes(
            b'@echo off\r\npy -3 "%~dp0update_scenarios.py" >nul || python "%~dp0update_scenarios.py" >nul\r\nstart "" "%~dp0index.html"\r\n')
        st = folder / "start.sh"
        st.write_text('#!/bin/sh\ncd "$(dirname "$0")" && python3 update_scenarios.py >/dev/null\n'
                      '(xdg-open index.html || open index.html) >/dev/null 2>&1\n', encoding="utf-8")
        st.chmod(0o755)


def write_scripts(root: str | Path) -> Path:
    """<root>/scripts/: the scenario updater for the whole output folder (it works on <root>/portable/scenarios)."""
    root = Path(root)
    add_updater(root / "scripts")
    return root / "scripts"
