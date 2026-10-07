# 06 · Compatibility and limits

The `.HMI` file does not name the display model in a form we read; the emulator uses what is in the file (resolution, pages, components,
images, fonts, code). "Verified" means: exercised on a real project file with the tests and a manual check of the emulator.

| | Status |
|---|---|
| **Verified** | One real project: **480×272** (landscape), 33 pages, 566 components, 46 images, 6 fonts, saved by **Nextion Editor 1.6.8.1** (the version is not recorded in the file; the project was also re-saved with **1.6.8.2** and parses identically) |
| **Other resolutions / orientations** | Implemented generically (the screen size comes from the file, `--screen` overrides it), **not verified** on a real file |
| **Other Nextion Editor versions** | **1.6.8.1 and 1.6.8.2 verified** (identical model and output; 1.6.8.2 just drops the old deleted sections: 54.7 → 47.5 MB). Other Editor versions are **not verified**: compare page/component/image/font counts and the coverage report warnings against the project in the Editor |
| **Other Nextion families** (Basic / Enhanced / Intelligent / Discovery) | **Not verified.** The container format is read from observations of one file plus public notes; a different format revision may fail to parse or show up as warnings in the coverage report |
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

## How the `.HMI` is read

Described in the docstring of `code/nextion_parser/parser/hmi.py`. In short: 28-byte directory records (append-only saves, deleted records
flagged), `N.pa` page sections, `N.is` image sections, `N.zi` font sections, and `main.HMI` holding the *order* of the resources – a
component's `pic` / `font` value and the `N` of a `page N` command are positions in that list. Based on the format
references [newmatik/nextion-hmi-writer](https://github.com/newmatik/nextion-hmi-writer) (MIT) and
[UNUF/nxt-doc](https://github.com/UNUF/nxt-doc) (no license stated) and on observations of the sample files; see the Credits in the
[README](../README.md). The reader itself is our own implementation.
