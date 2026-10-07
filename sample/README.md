# Sample files

`bioscale_research_new.HMI` is the sample project (480×272, saved by Nextion Editor 1.6.8.2, 47 MB); the tests and the examples use it. An
older save of the same project (Editor 1.6.8.1, `*_old.HMI`) is git-ignored and only used by one optional parity test. Next to the HMI the
repo has the configuration files that belong to it, so you can see what a finished setup looks like.

| Path | What it is | How it was made |
|---|---|---|
| `scenarios/variables.json` | Labels (hu/en), units, groups, ranges, presets and descriptions of the input variables | Written **by hand** (with AI help) from the discovered list and the HMI code |
| `scenarios/csv_profiles.json` | Targets of the CSV statistics import (mean / SD / CV / count, the page path, the waveform) | Written **by hand** for the sample's statistics page |
| `data/*.csv` | Example measurement data for the CSV import | Hand-made |
| `generated/variables.discovered.json` | Every input variable found by static analysis (reference, type, scope, initial value, where it is read, thresholds) | **Generated** by `discover` |
| `generated/variables.template.json` | Editable skeleton of `variables.json`: placeholder labels (the object names), page as group, initial values and probe values as presets | **Generated** by `discover` |
| `generated/csv_profiles.template.json` | A *guessed* `csv_profiles.json` (page, button path, the four value targets, waveform) | **Generated** by `discover`; check every entry |

Regenerate the `generated/` files with:

```bash
./scripts/run.sh discover sample/bioscale_research_new.HMI -o sample/generated
```

## Starting a setup for your own HMI

1. Run the generator (or `discover`) on your HMI; take `variables.template.json` and `csv_profiles.template.json` from the `discover/` output folder.
2. Copy them into a `scenarios/` folder next to your `.HMI` as `variables.json` and `csv_profiles.json`.
3. Edit them: replace the placeholder labels, add units and descriptions, correct the guessed CSV profile (the guess recognizes
   components whose names contain *quantity/count*, *mean/avg*, *sd/std* and *cv*, and the shortest button path to that page; the group
   field and the waveform button often need a manual fix).
4. Run the generator again – the emulator now shows your labels and offers the CSV import targets.

Without these files everything still works; variables are then listed by their technical names and the CSV targets are entered by hand.
