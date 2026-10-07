# 01 · Generate

```bash
./scripts/run.sh all path/to/YOUR.HMI        # everything into output/YOUR/
```

Open `output/YOUR/index.html` – the launcher page links the expert emulator, the basic (portable) emulator and the reports, and is
stamped with the source HMI's name, date and hash. Output goes to `./output/<file name>/` (or to `-o DIR`).

## Commands

| Command | What it does | Output |
|---|---|---|
| `summary FILE` | pages, components, event code, navigation | `summary/pages.json`, `navigation.mmd`, `navigation.html`, `summary.html` |
| `emulator FILE` | standalone browser emulator + help | `emulator/index.html`, `help.html`, `data.js`, `nextion_core.js`, `nextion_tools.js`, `i18n.js`, `img/` |
| `coverage FILE` | simulator coverage report | `coverage/coverage.html`, `coverage.json` |
| `unused FILE` | unused images / fonts / pages / components | `unused/unused.html`, `unused.csv`, `unused.json`, `img/` |
| `discover FILE` | input variables found by static analysis, plus editable skeletons of `variables.json` and a guessed `csv_profiles.json` | `discover/variables.discovered.json`, `variables.template.json`, `csv_profiles.template.json` |
| `portable FILE` | the **basic** variant for end users: simple mode only, scenarios found in its own `scenarios/` folder (see [04](04_scenarios.md)) | `<out>/index.html`, `data.js`, `*.js`, `img/`, `scenarios/` |
| `serve [DIR]` | local server for a generated folder: recordings made in the expert emulator are saved into the scenarios folder and appear in the basic emulator | – |
| `gui [FILE]` | the PySide6 window | – |
| `all FILE` | everything above + the portable package + the launcher `index.html` (the emulator is generated last so that it can link the reports) | all of the above |

## Options

`-o DIR` output folder · `--scenarios DIR` folder with scenarios, `variables.json`, `csv_profiles.json` (default: `<hmi folder>/scenarios`) ·
`--lenient` · and for `emulator` / `portable` / `all`: `--start PAGE`, `--screen WxH` (e.g. `800x480`), `--zoom Z|fit`, `--lang hu|en`
(default language of the emulator GUI; the user can switch it at run time).

**Exit codes:** `0` ok · `2` bad input · `4` everything was generated, but some scenarios no longer match this HMI (a CI job can
notice; `--lenient` turns it into `0`).

The command line and the reports are in **English**; the emulator GUI and its `help.html` are **bilingual (Hungarian / English)**.

Tests: `./scripts/run.sh --test`.
