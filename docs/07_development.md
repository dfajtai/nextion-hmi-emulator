# 07 · Development

## Layout

```
scripts/                              setup.sh, run.sh (+ .bat): venv, dependencies, run, tests
code/nextion_parser/
  builder_gui/                        PySide6 window, ALL GUI code lives here: main.ui (Qt Designer layout and the English texts),
                                      app.py (actions), jobs.py (runs a generation, no Qt)
  parser/                             REPLACEABLE input layer: anything producing a Project works
    model.py                          Project / Page / Component / Image / Font dataclasses (the contract)
    hmi.py                            .HMI reader (format notes in its docstring); codeutil.py: Nextion code statements
  analysis/                           pure functions Project -> plain data, no HTML, no files
    scenario.py  discover.py  unused.py  coverage.py  navigation.py
  reports/                            renders analysis results (HTML / CSV / JSON): coverage, unused, summary, discover;
                                      doc.py = document model (Card/Table/Section...) + one shared HTML renderer and theme
  emulator/                           the emulator generator
    model.py                          EmulatorData (typed content of data.js); help.py: the bilingual help.html
    builder.py                        EmulatorBuilder (data model + files), launcher.py, portable.py (scripts, start files)
    smoke.py                          headless runtime smoke test (Node); serve.py, update_scenarios.py (also shipped in packages)
    assets/                           nextion_core.js (interpreter), nextion_tools.js (CSV/statistics), i18n.js (GUI texts), smoke.js
    assets/ui/                        the emulator page SOURCE: index.html (markup), style.css, js/NN_*.js (one file per concern,
                                      concatenated in name order); ui.py assembles them into the single index.html
  i18n.py                             localized-field helper (loc);  cli.py: command line
code/tests/                           pytest by topic (test_parser, test_analysis, test_reports, test_cli, test_emulator_page,
                                      test_packaging, test_builder_gui) + helpers.py, conftest.py, fixtures/scenarios
sample/                               the sample HMI (Editor 1.6.8.2), its configs, CSV data and generated skeletons
```

Dependency direction: `cli` → `reports` → `analysis` → `parser`; `emulator` uses `parser` and `analysis`. Nothing below `reports`
produces HTML, and only `parser/hmi.py` knows the .HMI file format.

The page is assembled from `assets/ui/` at generation time – edit those files, never the generated `index.html`. The scripts
share one scope on purpose (no ES modules: they cannot be loaded from `file://`); new concerns get a new `NN_name.js`.

To add GUI text, put the key in **both** languages of `code/nextion_parser/emulator/assets/i18n.js` (a test checks that the two dictionaries have the same keys and
that every key used in the template exists).

## Everyday commands

```bash
./scripts/run.sh --test                  # tests (the HMI-based ones are skipped if the sample HMI is missing)
./scripts/run.sh all sample/bioscale_research_new.HMI
./scripts/run.sh discover sample/bioscale_research_new.HMI -o sample/generated   # refresh the committed generated samples
./scripts/build_easy.sh                  # dist/nextion-generator.pyz
```

Conventions are collected in [`CLAUDE.md`](../CLAUDE.md) (English everywhere in the repo; every GUI string in both languages; no
project-specific names in generic code; the page source lives in `assets/ui/`, never edit the generated `index.html`).
