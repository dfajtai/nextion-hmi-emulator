# 00 · Install and ways to run

Nothing but **Python 3.9+** is needed to run the generator – it uses only the standard library. `node` is optional (a headless smoke test
in the coverage report and part of the test-suite). The window (GUI) additionally needs PySide6.

Pick the way that fits the person:

| Who | Way | Needs |
|---|---|---|
| End user, no setup | **`nextion-generator.pyz`** – one file, put it next to the `.HMI` and double-click | Python 3.9+ |
| Anyone with the repository | **`generate.sh` / `generate.bat`** in the repo root – put the `.HMI` next to it and run | Python 3.9+ (the first run creates a private venv) |
| Prefers a window | **`scripts/gui.sh`** / `scripts\gui.bat` | PySide6 (installed on demand) |
| Developer | **`scripts/run.sh`** / `run.bat` – the full command line | Python 3.9+ |

## The single file (`nextion-generator.pyz`)

Put it **next to your `.HMI` file** and run it (double-click, or `python3 nextion-generator.pyz`). Everything is generated into
`output/<name>/` next to it and the launcher page opens in the browser. Several `.HMI` files in the folder are all processed. An optional
`scenarios/` folder next to the HMI supplies `variables.json`, `csv_profiles.json` and scenarios (see [02](02_project_setup.md)).

Build it (maintainers): `./scripts/build_easy.sh` or `scripts\build_easy.bat` → `dist/nextion-generator.pyz` (git-ignored; hand that one
file to the user).

## From the repository

```bash
git clone <repo-url> && cd nextion-hmi-emulator
cp /path/to/YOUR.HMI .           # next to generate.sh
./generate.sh                    # Windows: double-click generate.bat
```

`.HMI` files in the repository root are git-ignored. The first run creates the private virtual environment (`.venv`). You can also name the files:
`./generate.sh a.HMI b.HMI` (output goes to `output/` in the current folder). Errors are caught and explained, and the window waits for a key press
at the end, so a double-click never closes before you can read the result.

| Script | Purpose |
|---|---|
| `generate.sh` / `generate.bat` | process every `.HMI` next to it, open the launcher page |
| `scripts/run.sh` / `run.bat` | run any command (sets the environment up first); `--test` runs the tests |
| `scripts/setup.sh` / `setup.bat` | only create/refresh the venv (`.venv`; `NEXTION_VENV=/path` moves it, `PYTHON=python3.12` picks the interpreter; `--gui` adds PySide6) |
| `scripts/gui.sh` / `gui.bat` | the window (below) |
| `scripts/generate.bat` | Windows drag & drop: drop a `.HMI` onto it |
| `scripts/build_easy.sh` / `.bat` | build the single-file generator |

## The window (PySide6)

`./scripts/gui.sh` (Windows: `scripts\gui.bat`, you can drag a `.HMI` onto it) opens a small window: choose the HMI file (preselected when
one lies next to the script), output folder, optional scenarios folder and screen size, the emulator's default language, then
**Generate**; the log streams into the window and **Open result** opens the launcher page. The window itself is English only.

The script looks for PySide6 and installs only when it finds none: **1.** the project's private venv, **2.** the system Python, **3.** otherwise it
asks (about 80 MB, `code/requirements-gui.txt`) and installs `PySide6-Essentials` into the private venv. With the single-file generator use
your own Python's PySide6: `pip install PySide6-Essentials`, then `python3 nextion-generator.pyz gui`. PySide6 is LGPL licensed and is
installed by the user; it is not bundled here.

The layout is a Qt Designer file (`code/nextion_parser/builder_gui/main.ui`, edit it with `pyside6-designer main.ui`).

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `Permission denied` when starting `./generate.sh` or `./scripts/*.sh` (e.g. after downloading a zip, or on a share that drops file modes) | Make the scripts executable: `chmod u+x generate.sh scripts/*.sh` (or run them as `bash generate.sh`) |
| `python3: command not found`, or the scripts say Python 3 was not found | Install Python 3.9+ (Windows: python.org installer, tick *Add to PATH*; the `py` launcher is used on Windows) |
| The window does not open, the console mentions `Could not load the Qt platform plugin "xcb"` (Linux) | A system library is missing. On Debian/Ubuntu: `sudo apt install libxcb-cursor0` (and, if needed, `libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0`). Under Wayland you can try `QT_QPA_PLATFORM=wayland ./scripts/gui.sh` |
| The window opens but the file dialog (*Browse…*) does nothing or crashes | Usually the same Qt/desktop-integration problem. Type or paste the paths into the fields instead, or use `./generate.sh YOUR.HMI`, which needs no window |
| `gui.sh` wants to download PySide6 and fails | No internet / proxy. Install it yourself: `pip install PySide6-Essentials` (into the venv: `.venv/bin/pip`) |
| Creating the virtual environment fails (network drive, restricted folder) | Put it on a local disk: `NEXTION_VENV=$HOME/.nxvenv ./generate.sh` |
| The scenarios of the basic package do not show up | Open it through `start.bat` / `start.sh` (or run `update_scenarios`) so that `scenarios.js` is refreshed; see [04](04_scenarios.md) |
| Strange results after updating the repository | Remove the old environment (`rm -rf .venv`) and the stale `output/` folder, then run again |
