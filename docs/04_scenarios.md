# 04 · Scenarios, sharing and the basic package

A scenario is a list of steps executed on behalf of the MCU. Scenarios are `*.json` files (one per file, or `{"scenarios": [...]}`) in the
`scenarios/` folder (next to the `.HMI` by default; `variables.json` and `csv_profiles.json` live there too, see [02](02_project_setup.md)).
The easiest way to author one is the macro recorder of the expert emulator ([03](03_emulator.md)); this is the format it writes:

```json
{
  "name": {"hu": "Példa", "en": "Example"},
  "description": "What does the display show when the value is 12?",
  "page": "pageA",
  "steps": [
    {"say": {"hu": "Az MCU 12-re állítja", "en": "The MCU sets it to 12"}, "set": {"pageA.level.val": 12}},
    {"wait": 1500},
    {"say": "START", "click": "btnStart"},
    {"cmd": "page pageA"},
    {"ramp": {"ref": "pageA.level.val", "from": 100, "to": 0, "step": 10, "every": 500}},
    {"wave": {"ref": "pageB.wave0", "fn": "sine", "n": 300, "min": 40, "max": 200}}
  ]
}
```

`name`, `description` and `say` (and the `label`/`unit`/`group`/`description` fields of `variables.json`) are either plain text or an
object `{"hu": "...", "en": "..."}`; the GUI shows the selected language. Step types: `say`, `set`, `click`, `goto`, `cmd`, `wait`,
`ramp`, `wave`, `repeat`. References are `page.component.attribute`. `set` writes a variable directly: if the HMI code reloads it from
elsewhere (e.g. the language from EEPROM when the main page loads), follow the real user path with `click` steps instead.

## Basic (portable) package: sharing scenarios with trainers

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
