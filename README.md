# nextion-hmi-emulator

Turns a Nextion `.HMI` project file into an **offline browser emulator** of the display – with a scenario player, a macro recorder, CSV
import and a bilingual (HU/EN) interface – plus **analysis reports** (simulator coverage, unused resources, navigation). Built for demos,
training and testing of a device whose HMI changes: drop the new `.HMI` in, get a fresh emulator. Python standard library only.

## Quick start

```bash
git clone https://github.com/dfajtai/nextion-hmi-emulator.git && cd nextion-hmi-emulator
cp /path/to/YOUR.HMI .
./generate.sh          # Windows: double-click generate.bat
```

Everything lands in `output/YOUR/`; the launcher page `index.html` opens and links the emulator and the reports. Other ways (a single
`.pyz` file for end users, a window, the full command line): [00 · Install](docs/00_install.md).

## Documentation

|                                                              |                                                                   |
| ------------------------------------------------------------ | ----------------------------------------------------------------- |
| [00 · Install and ways to run](docs/00_install.md)           | requirements, the single file, `generate.sh`, the window, scripts |
| [01 · Generate](docs/01_generate.md)                         | commands, options, outputs, exit codes                            |
| [02 · Set up a project](docs/02_project_setup.md)            | `variables.json`, `csv_profiles.json`, templates from `discover`  |
| [03 · The emulator](docs/03_emulator.md)                     | modes, scenario player, recorder, CSV import                      |
| [04 · Scenarios and the basic package](docs/04_scenarios.md) | scenario format, sharing with trainers, auto-loading              |
| [05 · Reports](docs/05_reports.md)                           | coverage, unused resources, summary, discovery                    |
| [06 · Compatibility and limits](docs/06_compatibility.md)    | what it was tested on, supported components, the `.HMI` format    |
| [07 · Development](docs/07_development.md)                   | layout, layers, tests, conventions                                |
| [Sample files](sample/README.md)                             | the sample HMI, its configuration and generated skeletons         |

## Tested on

One real project: **480×272** landscape, 33 pages, 566 components, saved by **Nextion Editor 1.6.8.1** and **1.6.8.2** (identical result).
Other resolutions, Nextion families, Editor versions and the compiled `.tft` are **not verified** – run the generator and read the coverage
report for a new HMI. Details and the supported components: [06 · Compatibility](docs/06_compatibility.md).

## Credits

The `.HMI` container format is not officially documented. Understanding it relied on the work of others, which we gratefully reference:

- [newmatik/nextion-hmi-writer](https://github.com/newmatik/nextion-hmi-writer) (Newmatik GmbH, MIT) – a reverse-engineered, byte-level
  description of the Nextion Editor `.HMI` files.
- [UNUF/nxt-doc](https://github.com/UNUF/nxt-doc) – documentation of the Nextion file formats and protocols (no license is stated in the repository).

The reader in `code/nextion_parser/parser/hmi.py` is our own implementation, verified against real project files (see
[06 · Compatibility](docs/06_compatibility.md)). Nextion is a trademark of its owner; this project is not affiliated with it.

## License

MIT – see [LICENSE](LICENSE).
