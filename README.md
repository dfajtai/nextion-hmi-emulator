# nextion_parser

Turns a Nextion `.HMI` project file into

1. **summaries** (pages, components, event code, navigation),
2. a **browser emulator** with scenarios, a macro recorder, CSV import and a bilingual (HU/EN) GUI + help,
3. **reports** (simulator coverage, unused resources, variable discovery).

It needs nothing but the Python standard library. `node` is optional: it is used for the headless smoke test in the
coverage report and for part of the test-suite.

## Quick start

### Easy generator (for users, no setup)

One file, `nextion-generator.pyz`, needs only Python 3.9+. Put it **next to your `.HMI` file** and run it (double-click, or
`python3 nextion-generator.pyz`). Everything is generated into `output/<name>/` next to it and the launcher page opens in the
browser. Several `.HMI` files in the folder are all processed. An optional `scenarios/` folder next to the HMI supplies
`variables.json` / `csv_profiles.json` / scenarios. Build the file with `./scripts/build_easy.sh` (or `scripts\build_easy.bat`);
it appears in `dist/` (git-ignored) – hand that one file to the user.

### From the repository (developers)

Needs only Python 3.9+. Clone the repo and run – the first run creates the virtual environment by itself:

```bash
git clone <repo-url> && cd nextion-hmi-emulator
./scripts/run.sh all path/to/YOUR.HMI
# then open output/YOUR/index.html (launcher page) in a browser
```

Windows: drag the `.HMI` file onto `scripts\generate.bat` (it generates everything and opens the launcher page), or use
`scripts\run.bat all path\to\YOUR.HMI`.

| Script | Purpose |
|---|---|
| `scripts/run.sh` / `run.bat` | run any command (sets up the environment first if needed); `--test` runs the tests |
| `scripts/setup.sh` / `setup.bat` | only create/refresh the venv (`.venv`, override with `NEXTION_VENV=/path`; `PYTHON=python3.12` picks the interpreter) |
| `scripts/generate.bat` | Windows drag & drop: HMI file → everything + opens the result |

Output goes to `./output/<file name>/` (or to `-o DIR`).

| Command | What it does | Output |
|---|---|---|
| `summary FILE` | pages, components, event code, navigation | `summary/pages.json`, `navigation.mmd`, `navigation.html`, `summary.html` |
| `emulator FILE` | standalone browser emulator + help | `emulator/index.html`, `help.html`, `data.js`, `nextion_core.js`, `nextion_tools.js`, `i18n.js`, `img/` |
| `coverage FILE` | simulator coverage report | `coverage/coverage.html`, `coverage.json` |
| `unused FILE` | unused images / fonts / pages / components | `unused/unused.html`, `unused.csv`, `unused.json`, `img/` |
| `discover FILE` | simulation input variables found by static analysis | `discover/variables.discovered.json` |
| `portable FILE` | **basic** variant for end users (trainer cells): simple mode only (cannot be switched to expert), no built-in scenarios, no reports/help, empty `scenarios/` folder next to `index.html` | `<out>/index.html`, `data.js`, `*.js`, `img/`, `scenarios/` |
| `serve [DIR]` | local server for a generated folder (default port 8765, opens the browser): the scenarios folder is shared – recordings saved in the expert emulator appear in the basic emulator automatically | – |
| `all FILE` | everything above + the portable package + a launcher `index.html` (stamped with the source HMI's name, date and hash) (the emulator is generated last so that it can link the reports) | all of the above |

Options: `--lenient` (do not fail on scenarios that no longer match the HMI: by default the tool still generates everything but exits with code 4, so a CI job notices), `-o DIR` (output folder), `--scenarios DIR` (scenarios + `variables.json`; default `<hmi folder>/scenarios`),
and for `emulator` / `all`: `--start PAGE`, `--screen WxH` (e.g. `800x480`), `--zoom Z|fit`, `--lang hu|en`
(default GUI language, the user can switch at run time).

Tests: `./scripts/run.sh --test`.

The command line and the reports are in **English**. The emulator GUI and `help.html` are **bilingual (Hungarian / English)**.

## The emulator

A folder of static files that works offline (`file://` is fine). It runs the real event code of the HMI (clicks, page loads,
timers) in a small interpreter of the Nextion language. It is not the real display: fonts are system fonts, timing is
approximate, and the serial (MCU) side is simulated by scenarios.

* **Simple mode**: the display, a caption window and a scenario player (step through or play automatically).
* **Expert mode**: everything – macro recorder, variable panels, MCU command line, display controls, reports menu, hover tooltips.
* **Language**: the `Magyar / English` selector in the header switches the whole GUI at run time; the choice is remembered
  (`localStorage`) and the help follows it. `?lang=en` in the URL overrides it.
* **Help**: the `? Help` link opens `help.html` (a practical manual of the whole simulator, bilingual).

Full usage is described in `help.html`; a short overview:

### Scenario player

A scenario is a list of steps executed on behalf of the MCU (see the format below). Controls: **↺ From start**, **◀ Previous**, one **▶ Play / ⏸ Pause** toggle, **Next ▶**, a step list (click to jump) and a pace selector
(0.5×/1×/2×/4×, or **Even pause**: the same N seconds after every step, the scenario's own waits are ignored). Clicking the display during
playback stops it. Playback always starts from the
scenario's own initial state; the initial page is shown for about a second before the first click. A button press is
announced with a magenta frame (the button name is shown in expert mode only) before the click happens. If you changed
something by hand, the emulator re-synchronizes by replaying the steps so far.

### Caption window

Large caption of the current step, with a badge (`CAPTION` / `STEP` / `STATUS`) and `step n / N`. Errors appear in a separate
red bubble (only when there are any); the **History** button lists all captions and errors so far.

### Macro recorder (expert)

`1. Record → 2. Edit → 3. Save`. One button starts/stops recording (from a clean state on the chosen start page). Clicks, variable changes,
page jumps and MCU commands are recorded. There is **no automatic timing**: add `+ Delay` rows (seconds + optional caption), or tick
"record real time as delays". Every step can have a caption; rows can be reordered, deleted, or edited as JSON. Any scenario can be
loaded back into the recorder (`✎ Edit in the recorder`) and extended (`➕ Continue from the end`). Saving downloads a `.json`
(same id/file name when the name is unchanged; a localized name/description is preserved).

### CSV import

`Load scenario / CSV…` (or drag & drop). Two modes:

* **Statistics**: a value column (optionally split by a group column) → count, mean, sample SD (n−1), CV written to the target
  variables, plus the raw values drawn as a waveform. Targets and navigation come from `scenarios/csv_profiles.json`.
* **Time series**: the header names variables (full reference, label from `variables.json`, or unique name); special columns
  `t_ms`, `wait_ms`, `say`, `goto`, `cmd`.

Samples: `sample/data/meresek.csv`, `sample/data/akku_idosor.csv`.

### Display controls (expert)

Screen size, zoom (`fit` adapts to the available space), hitboxes, and "idle return jump": the HMI timers jump back to the main page
after inactivity; the emulator blocks this by default so it does not jump around.

### Portable basic package

`portable FILE -o DIR` writes a self-contained folder (copy it anywhere). It is locked to simple mode and keeps its scenarios in its own
`scenarios/` folder, which is the single place for them. A static page cannot list a folder by itself, so discovery works through
`scenarios.js`, a bundle of that folder:

* **Double-click `start.bat` / `start.sh`** (needs Python 3): refreshes `scenarios.js` and opens the emulator from disk. The scenarios
  in the folder are found automatically.
* Scenarios recorded in the expert emulator land in the browser's Downloads folder: drag that folder onto `update_scenarios.bat`
  (or `python3 update_scenarios.py <folder>`); scenario `.json` files are copied into `scenarios/` (unrelated `.json` files are ignored) and
  the bundle is rebuilt.
* With `serve` (or `python3 serve.py --open` inside a package) no copying is needed: the expert recorder writes into the
  folder directly and the basic emulator re-checks it every 3 s.
* Without Python: **Open folder…** (Chromium-based browsers) or **Load scenario…** / drag & drop in the page.

In a full `all` output the same scenarios folder is `portable/scenarios/`; `scripts/update_scenarios.*` there refreshes both the basic
and the expert emulator.

## Scenarios

Files in the `scenarios/` folder (next to the `.HMI` by default):

* `*.json` – scenarios (one per file, or `{"scenarios": [...]}`),
* `variables.json` – labels / units / groups of variables (used in captions and the CSV import),
* `csv_profiles.json` – targets of the CSV statistics.

```json
{
  "name": {"hu": "Alacsony akku", "en": "Low battery"},
  "description": "What does the display show at 12 % charge?",
  "page": "pageMainAuto",
  "steps": [
    {"say": {"hu": "Az MCU 12%-ot jelent", "en": "The MCU reports 12 %"}, "set": {"pageMainAuto.charge_level.val": 12}},
    {"wait": 1500},
    {"say": "START", "click": "bstart"},
    {"cmd": "page pageMainAuto"},
    {"ramp": {"ref": "pageMainAuto.charge_level.val", "from": 100, "to": 0, "step": 10, "every": 500}},
    {"wave": {"ref": "pageStat2.s0", "fn": "sine", "n": 300, "min": 40, "max": 200}}
  ]
}
```

`name`, `description` and `say` (and the `label`/`unit`/`group`/`description` fields of `variables.json`) are either plain text or an
object `{"hu": "...", "en": "..."}`; the GUI shows the selected language. Step types: `say`, `set`, `click`, `goto`, `cmd`, `wait`,
`ramp`, `wave`, `repeat`. References are `page.component.attribute`. `set` writes a variable directly: if the HMI code reloads it from
elsewhere (e.g. the language from EEPROM when the main page loads), follow the real user path with `click` steps instead.

`sample/scenarios/` contains no scenarios, only `variables.json` and `csv_profiles.json`; scenarios are recorded in the expert emulator.

## Reports

All reports are HTML and in English; they open from the emulator's `Reports` menu.

* **Coverage** – how much of the HMI the emulator reproduces: structure, component/attribute support, code commands, resources,
  a headless runtime smoke test (needs `node`) and the scenarios (validity, runs, touched inputs/pages).
* **Unused resources** – unreferenced images (with preview and the Editor's resource id), fonts, pages, superfluous components and the
  file's "dead" (deleted-section) content, to help "compressing" the HMI. The `.HMI` file is never modified; deletion is done in the
  Nextion Editor. References assigned in code (`obj.pic=N`, `pic`/`picq`/`xpic`, `xstr`) are taken into account; non-literal ones are
  reported as *uncertain*.
* **Summary / navigation** – pages, start-up program, jumps between pages (the Mermaid diagram needs internet access).
* **Discovery** – variables the code reads but never writes (likely fed by the MCU), with the thresholds they are compared with.

## How the `.HMI` is read

Described in the docstring of `code/nextion_parser/hmi.py`. In short: 28-byte directory records (append-only saves, deleted records
flagged), `N.pa` page sections, `N.is` image sections, `N.zi` font sections, and `main.HMI` holding the *order* of the resources – a
component's `pic` / `font` value and the `N` of a `page N` command are positions in that list. Based on
[newmatik/nextion-hmi-writer](https://github.com/newmatik/nextion-hmi-writer), [UNUF/nxt-doc](https://github.com/UNUF/nxt-doc) and
observations on the sample file.

## Project layout

```
scripts/                              setup.sh, run.sh (+ .bat): venv, dependencies, run, tests
code/nextion_parser/
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
code/tests/                           pytest (+ fixtures/scenarios used by the tests)
sample/                               sample configs and CSV data (sample HMI is git-ignored)
```

Dependency direction: `cli` → `reports` → `analysis` → `parser`; `emulator` uses `parser` and `analysis`. Nothing below `reports`
produces HTML, and only `parser/hmi.py` knows the .HMI file format.

The page is assembled from `assets/ui/` at generation time – edit those files, never the generated `index.html`. The scripts
share one scope on purpose (no ES modules: they cannot be loaded from `file://`); new concerns get a new `NN_name.js`.

To add GUI text, put the key in **both** languages of `code/nextion_parser/emulator/assets/i18n.js` (a test checks that the two dictionaries have the same keys and
that every key used in the template exists).

## What it works with

The `.HMI` file does not name the display model in a form we read; the emulator uses what is in the file (resolution, pages, components,
images, fonts, code). "Verified" means: exercised on a real project file with the tests and a manual check of the emulator.

| | Status |
|---|---|
| **Verified** | One real project: **480×272** (landscape), 33 pages, 566 components, 46 images, 6 fonts, saved by the Nextion Editor (version not recorded in the file) |
| **Other resolutions / orientations** | Implemented generically (the screen size comes from the file, `--screen` overrides it), **not verified** on a real file |
| **Other Nextion families** (Basic / Enhanced / Intelligent / Discovery, other Editor versions) | **Not verified.** The container format is read from observations of one file plus public notes; a different format revision may fail to parse or show up as warnings in the coverage report |
| **Only the `.HMI` project file** | Not the compiled `.tft`, not a live device |

Component types (type id in brackets). "In the sample" = present in the verified project:

| Component | Support | In the sample |
|---|---|---|
| Page (121), button (98), text (116), number (54), xfloat (59), picture (112), hotspot (109), timer (51), variable (52) | full | yes (all) |
| Slider (1), waveform (0), radio button (57) | partial: slider only the fill and not draggable; waveform grid + series from `add`/`wave` (no scrolling/`addt`); radio not clickable | yes |
| Checkbox (56), progress bar (106) | partial (progress bar: simple fill; checkbox not clickable) | no – implemented, **never exercised on a real file** |
| Any other type | **not supported**: not drawn, reported as "unsupported" in the coverage report | – |

Code commands: `page`, `int`, `cov`, `covx`, `substr`, `btlen`, `strlen`, `wepo`, `repo`, `add`, `cle`, `click`, `vis`, `print`, `prints`,
`printh` are interpreted; `addt`, `bkcmd`, `delay`, `doevents`, `get`, `ref`, `rest`, `sleep`, `thsp`, `thup`, `tsw` are accepted and
ignored; everything else is reported as unknown. The serial (MCU) side is
only simulated by scenarios.

**How to check a new HMI quickly:** run the generator and open the *coverage* report – it lists the component types and commands the
emulator does not know, the pages it could not reach, and the unreadable parts of the file.

## Known limitations

* See "What it works with" above: only one real project has been verified.
* The initial visibility of components (`vis`) is not stored in the file; `.zi` fonts cannot be rendered (system font, glyph height from the file).
* Slider, checkbox and radio button are drawn roughly; waveform data only comes from `wave` / `add` steps; the serial protocol is not
  modelled; the duration of a long press is not recorded.
* The HMI's own texts (button captions, ...) do not follow the GUI language – the HMI selects them with its own `lang` variable.
