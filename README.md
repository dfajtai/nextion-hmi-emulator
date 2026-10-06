# nextion_parser

Turns a Nextion `.HMI` project file into

1. **summaries** (pages, components, event code, navigation),
2. a **browser emulator** with scenarios, a macro recorder, CSV import and a bilingual (HU/EN) GUI + help,
3. **reports** (simulator coverage, unused resources, variable discovery).

It needs nothing but the Python standard library. `node` is optional: it is used for the headless smoke test in the
coverage report and for part of the test-suite.

## Quick start

```bash
cd nextion_parser
./code/setup_and_run.sh all sample/bioscale_research.HMI
# then open output/bioscale_research/emulator/index.html in a browser
```

On the first run the script creates a private virtual environment (`.venv`, override with `NEXTION_VENV=/path`),
installs `code/requirements.txt`, activates it and runs the tool inside it. Output goes to `./output/<file name>/`
(or to `-o DIR`).

| Command | What it does | Output |
|---|---|---|
| `summary FILE` | pages, components, event code, navigation | `summary/pages.json`, `navigation.mmd`, `navigation.html`, `summary.html` |
| `emulator FILE` | standalone browser emulator + help | `emulator/index.html`, `help.html`, `data.js`, `nextion_core.js`, `nextion_tools.js`, `i18n.js`, `img/` |
| `coverage FILE` | simulator coverage report | `coverage/coverage.html`, `coverage.json` |
| `unused FILE` | unused images / fonts / pages / components | `unused/unused.html`, `unused.csv`, `unused.json`, `img/` |
| `discover FILE` | simulation input variables found by static analysis | `discover/variables.discovered.json` |
| `portable FILE` | **basic** variant for end users (trainer cells): simple mode only (cannot be switched to expert), no built-in scenarios, no reports/help, empty `scenarios/` folder next to `index.html` | `<out>/index.html`, `data.js`, `*.js`, `img/`, `scenarios/` |
| `serve [DIR]` | local server for a generated folder (default port 8765, opens the browser): the scenarios folder is shared – recordings saved in the expert emulator appear in the basic emulator automatically | – |
| `all FILE` | everything above + the portable package + a launcher `index.html` (the emulator is generated last so that it can link the reports) | all of the above |

Options: `-o DIR` (output folder), `--scenarios DIR` (scenarios + `variables.json`; default `<hmi folder>/scenarios`),
and for `emulator` / `all`: `--start PAGE`, `--screen WxH` (e.g. `800x480`), `--zoom Z|fit`, `--lang hu|en`
(default GUI language, the user can switch at run time).

Tests: `./code/setup_and_run.sh --test`.

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
(1×/2×/4×, or **Even pause**: the same N seconds after every step, the scenario's own waits are ignored). Clicking the display during
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

`portable FILE -o DIR` writes a self-contained folder (copy it anywhere, open `index.html`). It is locked to simple mode and ships
with an empty `scenarios/` folder. Record scenarios in the expert emulator, save the `.json` files into that folder, and in the basic
emulator press **Open folder…** (Chromium-based browsers) or **Load scenario…** / drag & drop the files. A static page cannot list a
folder by itself, so without a server the folder has to be selected once per session.
Without a server: put the `.json` files into `scenarios/` and run `scripts/update_scenarios.bat` / `.sh` (Python 3) – it rewrites
`scenarios.js`, which the emulator pages load from disk (a portable package carries its own copy next to `index.html`).
With `serve` (or `python3 start.py --open` inside a portable package, which needs only Python) the scenarios folder is read
automatically (re-checked every 3 s in the basic emulator) and the expert recorder writes into it directly.

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
code/setup_and_run.sh              venv + dependencies + run
code/nextion_parser/hmi.py         .HMI reader
code/nextion_parser/summary.py     JSON / Mermaid / HTML summaries
code/nextion_parser/emulator.py    emulator generator (templates/)
code/nextion_parser/helpdoc.py     bilingual help.html
code/nextion_parser/coverage.py    coverage report
code/nextion_parser/unused.py      unused-resource report
code/nextion_parser/discover.py    MCU input discovery, variables.json merge
code/nextion_parser/scenario.py    scenario loading and validation
code/nextion_parser/i18n.py        localized-field helper (loc)
code/nextion_parser/cli.py         command line
code/nextion_parser/templates/     nextion_core.js (interpreter), nextion_tools.js (CSV/statistics), i18n.js (GUI texts),
                                   emulator.html, smoke.js (headless smoke test)
code/tests/                        pytest (+ fixtures/scenarios used by the tests)
sample/                            sample HMI, scenarios, CSV data
```

To add GUI text, put the key in **both** languages of `templates/i18n.js` (a test checks that the two dictionaries have the same keys and
that every key used in the template exists).

## Known limitations

* Only one sample project (480×272) has been tried; other Nextion families / Editor versions may differ. The coverage report lists the
  components and commands the emulator does not know.
* The initial visibility of components (`vis`) is not stored in the file; `.zi` fonts cannot be rendered (system font, glyph height from the file).
* Slider, checkbox and radio button are drawn roughly; waveform data only comes from `wave` / `add` steps; the serial protocol is not
  modelled; the duration of a long press is not recorded.
* The HMI's own texts (button captions, ...) do not follow the GUI language – the HMI selects them with its own `lang` variable.
