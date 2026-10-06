# CLAUDE.md

Python tool (`nextion_parser`) that parses Nextion `.HMI` files and generates summaries, an offline browser emulator and reports.
Standard library only; `node` is optional (smoke test, some tests). User-facing conversation language: Hungarian; everything in the repo is English.

## Commands
- Run: `./scripts/run.sh <summary|emulator|portable|coverage|unused|discover|all> FILE.HMI [-o DIR] [--scenarios DIR] [--lang hu|en]`
- Tests: `./scripts/run.sh --test` (pytest; HMI-based tests are skipped when `sample/*.HMI` is missing)
- Regenerate sample output: `./scripts/run.sh all sample/bioscale_research.HMI` (`output/` is git-ignored)

## Layout
- `code/nextion_parser/hmi.py` – `.HMI` reader (format notes in its docstring). Resource ids (`pic`, `font`, `page N`) are positions in the `main.HMI` lists.
- `code/nextion_parser/emulator.py` – generator; copies `templates/` (`emulator.html`, `nextion_core.js` interpreter, `nextion_tools.js` CSV/stats, `i18n.js` GUI dictionaries) and writes `data.js`.
- `portable` command = basic variant: `DATA.portable`, locked to simple mode, no built-in scenarios, empty `scenarios/` folder, no help/reports.
- `serve.py` – stdlib server with `api/scenarios` (GET list / POST save); copied into portable packages as `start.py`. The emulator syncs with it only over http(s) (`syncServer`); `file://` must keep working.
- `update_scenarios.py` – standalone; bundles `scenarios/*.json` into `scenarios.js` (`window.NX_SCENARIOS`) that every emulator page loads, so no server is needed. Generated into `<out>/scripts/` and into portable packages.
- `all` writes `<out>/index.html` (launcher), `emulator/`, `portable/` and the reports.
- `code/tests/fixtures/scenarios/` – scenarios used only by tests; `sample/scenarios/` holds only `variables.json` and `csv_profiles.json`.

## Conventions
- Code, comments, docstrings, tests, CLI messages, reports and markdown are English. Only the web GUI (`i18n.js`, `helpdoc.py`) and scenario/variable JSON fields are bilingual.
- Every GUI string goes into **both** languages of `templates/i18n.js`; no hard-coded text in the emulator script (a test enforces it). Localized fields are `{"hu":…,"en":…}` or plain text.
- The `.HMI` input is never modified. The emulator must work from `file://` (no fetch, no server).
- Keep `emulator.html` handlers/functions intact when editing: tests check for lost functions and dangling handlers.
- Do not add Claude/Anthropic co-author trailers to commits.
