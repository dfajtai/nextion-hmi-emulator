# CLAUDE.md

Python tool (`nextion_parser`) that parses Nextion `.HMI` files and generates summaries, an offline browser emulator and reports.
Standard library only; `node` is optional (smoke test, some tests). User-facing conversation language: Hungarian; everything in the repo is English.

## Commands
- Run: `./scripts/run.sh <summary|emulator|portable|coverage|unused|discover|all> FILE.HMI [-o DIR] [--scenarios DIR] [--lang hu|en]`
- Tests: `./scripts/run.sh --test` (pytest; tests live in `code/tests/test_*.py` by topic, shared helpers in `helpers.py`, the `project` fixture in `conftest.py`; HMI-based tests are skipped when the sample HMI is missing)
- Regenerate sample output: `./scripts/run.sh all sample/bioscale_research_new.HMI` (`output/` is git-ignored)

## Layout
- Layers (dependency direction `cli` → `reports` → `analysis` → `parser`; `emulator` uses `parser` + `analysis`):
  - `code/nextion_parser/parser/` – replaceable input layer. `model.py` is the contract (`Project`...), `hmi.py` the .HMI reader (format notes in its docstring; resource ids `pic`, `font`, `page N` are positions in the `main.HMI` lists). Only this layer knows the file format.
  - `analysis/` – pure functions Project → plain data (scenario validation, discovery, unused, coverage, navigation). No HTML, no file writing.
  - `reports/` – turns analysis results into HTML/CSV/JSON files. Reports build a `doc.Doc` model (cards, tables, details…) and `doc.render` produces the page; do not hand-write report HTML or CSS in a report module. Inline cell HTML must be built with `esc`/`code`/`tag`.
  - `emulator/` – `EmulatorBuilder` (+ `EmulatorData` model) writes the emulator and its `help.html`; `assets/` holds the static front-end: `nextion_core.js` interpreter, `nextion_tools.js` CSV/stats, `i18n.js` GUI dictionaries, and `assets/ui/` = the page source (`index.html` shell, `style.css`, `js/NN_*.js` concatenated in name order into one classic script by `emulator/ui.py`; no ES modules because of `file://`); `data.js` is the only generated front-end file.
- `builder_gui/` – the PySide6 window (`scripts/gui.sh|bat` – they use PySide6 from the venv, else from the system Python, else install it into the venv –, `nextion_parser gui`); PySide6 is an OPTIONAL dependency (`code/requirements-gui.txt`, installed by `setup.sh --gui`), the rest of the tool stays standard-library only. Keep ALL GUI-specific code here. The window is English only (not translated): layout and texts are in `main.ui` (Qt Designer); `app.py` binds actions; `jobs.py` runs a generation without importing Qt. Worker threads talk to the window only through Qt signals. Do not rename object names without updating `main.ui` and `app.py` (a test checks they agree).
- `easy.py` + `scripts/build_easy.*` – single-file `dist/nextion-generator.pyz` (zipapp, entry `nextion_parser.easy:run`): no arguments = process every `.HMI` next to the file; with arguments it is the normal CLI. Package data is read through `importlib.resources` (never `__file__` paths) so it works from inside the zip.
- `portable` command = basic variant: `DATA.portable`, locked to simple mode, no built-in scenarios, empty `scenarios/` folder, no help/reports.
- `serve.py` – stdlib server with `api/scenarios` (GET list / POST save); copied into portable packages as `serve.py`. The emulator syncs with it only over http(s) (`syncServer`); `file://` must keep working.
- `update_scenarios.py` – standalone; bundles `scenarios/*.json` into `scenarios.js` (`window.NX_SCENARIOS`) that every emulator page loads, so no server is needed. The scenarios folder is `<out>/portable/scenarios/`. Generated into `<out>/scripts/` and into portable packages (with `start.bat/.sh`).
- `all` writes `<out>/index.html` (launcher), `emulator/`, `portable/` and the reports.
- Docs: `README.md` is a short entry point (summary, quick start, TOC, one-line 'tested on'); the details are numbered topic pages in `docs/` (00 install → 07 development). Keep that structure; a test checks links and that the README stays short. Update `docs/06_compatibility.md` whenever something new is verified.
- `sample/README.md` explains the committed sample files; `sample/generated/` is the output of `discover` (regenerate it when the discovery or the templates change). `analysis/csvprofile.py` only GUESSES a `csv_profiles.json` skeleton from component names.
- `code/tests/fixtures/scenarios/` – scenarios used only by tests; `sample/scenarios/` holds only `variables.json` and `csv_profiles.json`.

## Conventions
- Code, comments, docstrings, tests, CLI messages, reports and markdown are English. Only the web GUI (`i18n.js`, `helpdoc.py`) and scenario/variable JSON fields are bilingual.
- Every GUI string goes into **both** languages of `emulator/assets/i18n.js`; no hard-coded text in the emulator script (a test enforces it). Localized fields are `{"hu":…,"en":…}` or plain text.
- Nothing generic (front-end assets, help text, docstrings) may name a particular project's pages/components: real names come from the project (`emulator/examples.py` → `DATA.examples`, `{page}`/`{ref}` in i18n texts). A test enforces it.
- The `.HMI` input is never modified. The emulator must work from `file://` (no fetch, no server).
- Edit the page in `emulator/assets/ui/`, never the generated `index.html`. Keep handlers/functions intact when editing: tests check for lost functions and dangling handlers.
- Do not add Claude/Anthropic co-author trailers to commits.
