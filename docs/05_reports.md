# 05 · Reports

All reports are HTML and in English; they open from the emulator's `Reports` menu.

* **Coverage** – how much of the HMI the emulator reproduces: structure, component/attribute support, code commands, resources,
  a headless runtime smoke test (needs `node`) and the scenarios (validity, runs, touched inputs/pages).
* **Unused resources** – unreferenced images (with preview and the Editor's resource id), fonts, pages, superfluous components and the
  file's "dead" (deleted-section) content, to help "compressing" the HMI. The `.HMI` file is never modified; deletion is done in the
  Nextion Editor. References assigned in code (`obj.pic=N`, `pic`/`picq`/`xpic`, `xstr`) are taken into account; non-literal ones are
  reported as *uncertain*.
* **Summary / navigation** – pages, start-up program, jumps between pages (the Mermaid diagram needs internet access).
* **Discovery** – variables the code reads but never writes (likely fed by the MCU), with the thresholds they are compared with.
