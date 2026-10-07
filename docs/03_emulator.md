# 03 · The emulator

A folder of static files that works offline (`file://` is fine). It runs the real event code of the HMI (clicks, page loads,
timers) in a small interpreter of the Nextion language. It is not the real display: fonts are system fonts, timing is
approximate, and the serial (MCU) side is simulated by scenarios.

* **Simple mode**: the display, a caption window and a scenario player (step through or play automatically).
* **Expert mode**: everything – macro recorder, variable panels, MCU command line, display controls, reports menu, hover tooltips.
* **Language**: the `Magyar / English` selector in the header switches the whole GUI at run time; the choice is remembered
  (`localStorage`) and the help follows it. `?lang=en` in the URL overrides it.
* **Help**: the `? Help` link opens `help.html` (a practical manual of the whole simulator, bilingual).

The full manual is `help.html` next to the emulator (bilingual); a short overview:

## Scenario player

A scenario is a list of steps executed on behalf of the MCU (see [04](04_scenarios.md)). Controls: **↺ From start**, **◀ Previous**, one **▶ Play / ⏸ Pause** toggle, **Next ▶**, a step list (click to jump) and a pace selector
(0.5×/1×/2×/4×, or **Even pause**: the same N seconds after every step, the scenario's own waits are ignored). Clicking the display during
playback stops it. Playback always starts from the
scenario's own initial state; the initial page is shown for about a second before the first click. A button press is
announced with a magenta frame (the button name is shown in expert mode only) before the click happens. If you changed
something by hand, the emulator re-synchronizes by replaying the steps so far.

## Caption window

Large caption of the current step, with a badge (`CAPTION` / `STEP` / `STATUS`) and `step n / N`. Errors appear in a separate
red bubble (only when there are any); the **History** button lists all captions and errors so far.

## Macro recorder (expert)

`1. Record → 2. Edit → 3. Save`. One button starts/stops recording (from a clean state on the chosen start page). Clicks, variable changes,
page jumps and MCU commands are recorded. There is **no automatic timing**: add `+ Delay` rows (seconds + optional caption), or tick
"record real time as delays". Every step can have a caption; rows can be reordered, deleted, or edited as JSON. Any scenario can be
loaded back into the recorder (`✎ Edit in the recorder`) and extended (`➕ Continue from the end`). Saving downloads a `.json`
(same id/file name when the name is unchanged; a localized name/description is preserved).

## CSV import

`Load scenario / CSV…` (or drag & drop). Two modes:

* **Statistics**: a value column (optionally split by a group column) → count, mean, sample SD (n−1), CV written to the target
  variables, plus the raw values drawn as a waveform. Targets and navigation come from `scenarios/csv_profiles.json`.
* **Time series**: the header names variables (full reference, label from `variables.json`, or unique name); special columns
  `t_ms`, `wait_ms`, `say`, `goto`, `cmd`.

Samples: `sample/data/meresek.csv`, `sample/data/akku_idosor.csv`.

## Screenshot (both modes)

The **📷 Screenshot…** button under the display saves the current picture of the display as a PNG in its native resolution (e.g. 480×272),
without the highlight frames or hitboxes. Chromium-based browsers open a real *Save as* window; other browsers use their normal download.
**📋 Copy** puts the same picture on the clipboard (paste it into a document or mail; hidden in browsers without clipboard-image support).
It also works when the page is opened from disk (the pictures are embedded in `images.js` for this purpose).

## Display controls (expert)

Screen size, zoom (`fit` adapts to the available space), hitboxes, and "idle return jump": the HMI timers jump back to the main page
after inactivity; the emulator blocks this by default so it does not jump around.
