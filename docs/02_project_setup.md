# 02 · Set up a project: variables and CSV profile

Everything works without any configuration; these optional files in a `scenarios/` folder next to your `.HMI` make the emulator friendlier:

| File | Purpose | Without it |
|---|---|---|
| `variables.json` | labels (hu/en), units, groups, ranges, presets and descriptions of the MCU input variables | variables are listed by their technical names |
| `csv_profiles.json` | targets of the CSV statistics import: into which variables mean / SD / CV / count go, the button path to that page, the waveform | the targets are entered by hand in the import dialog |
| `*.json` scenarios | see [04](04_scenarios.md) | – |

The parser does **not** produce them – they are hand-written configuration. To make that easy, `discover` writes skeletons:

1. Run the generator (or `discover`) on your HMI; take `variables.template.json` and `csv_profiles.template.json` from the `discover/` output folder.
2. Copy them into `scenarios/` next to your `.HMI` as `variables.json` and `csv_profiles.json`.
3. Edit them: replace the placeholder labels, add units and descriptions, correct the *guessed* CSV profile (the guess recognizes components whose
   names contain *quantity/count*, *mean/avg*, *sd/std*, *cv* and the shortest button path to that page; the group field and the waveform
   button often need a manual fix).
4. Generate again – the emulator now shows your labels and offers the CSV targets.

`name`, `description`, `say` and the `label` / `unit` / `group` / `description` fields can be plain text or `{"hu": "...", "en": "..."}`.

A finished example (hand-written for the sample) and the generated skeletons for the sample are committed in [`sample/`](../sample/README.md).
