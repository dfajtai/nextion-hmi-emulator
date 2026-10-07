"""Updates scenarios.js from the scenarios folder so that the emulator works from disk without any server.

Standard library only; runs anywhere Python 3 is installed (double-click update_scenarios.bat / .sh next to it).
Optionally pass folders (or drag them onto the .bat): scenario .json files found there (e.g. the browser's Downloads
folder after recording in the expert emulator) are first copied into the scenarios folder.
Placement decides what it does:
  * <package>/update_scenarios.py   (next to index.html)  -> scenarios folder: <package>/scenarios, writes <package>/scenarios.js
  * <output>/scripts/update_scenarios.py                  -> scenarios folder: <output>/portable/scenarios, writes scenarios.js
                                                             into every sibling folder that holds an emulator (emulator/, portable/)
This file is also copied into generated folders by nextion_parser.
"""
import json
import shutil
import sys
from pathlib import Path

RESERVED = {"variables.json", "variables.discovered.json", "csv_profiles.json"}


def is_scenario(data) -> bool:
    """True for the shapes the emulator accepts: {steps: [...]}, {scenarios: [...]} or a list of those."""
    if isinstance(data, list):
        return bool(data) and all(is_scenario(x) for x in data)
    return isinstance(data, dict) and (isinstance(data.get("steps"), list) or isinstance(data.get("scenarios"), list))


def collect(folder: Path) -> tuple[list, list]:
    items, problems = [], []
    for f in sorted(folder.glob("*.json")):
        if f.name in RESERVED:
            continue
        try:
            items.append({"name": f.name, "data": json.loads(f.read_text(encoding="utf-8-sig"))})
        except (OSError, ValueError) as e:
            problems.append(f"{f.name}: {e}")
    return items, problems


def import_from(source: Path, dest: Path) -> list[str]:
    """Copy scenario files that are missing or newer in `dest`; unrelated .json files are ignored."""
    copied = []
    for f in sorted(source.glob("*.json")):
        if f.name in RESERVED:
            continue
        try:
            if not is_scenario(json.loads(f.read_text(encoding="utf-8-sig"))):
                continue
        except (OSError, ValueError):
            continue
        t = dest / f.name
        if not t.exists() or f.stat().st_mtime > t.stat().st_mtime + 1:
            shutil.copy2(f, t)
            copied.append(f.name)
    return copied


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    if (here / "index.html").is_file():
        scen, targets = here / "scenarios", [here]
    else:
        root = here.parent
        scen = root / "portable" / "scenarios"
        targets = [d for d in sorted(root.iterdir()) if (d / "index.html").is_file() and (d / "data.js").is_file()]
    scen.mkdir(parents=True, exist_ok=True)
    for src in (argv if argv is not None else sys.argv[1:]):
        p = Path(src)
        if p.is_dir() and p.resolve() != scen.resolve():
            for n in import_from(p, scen):
                print(f"  copied from {p}: {n}")
        else:
            print(f"  ! not a folder (skipped): {src}")
    items, problems = collect(scen)
    text = "window.NX_SCENARIOS=" + json.dumps(items, ensure_ascii=False) + ";\n"
    for d in targets:
        (d / "scenarios.js").write_text(text, encoding="utf-8")
    print(f"Scenarios folder: {scen}")
    print(f"{len(items)} scenario file(s) written into: " + (", ".join(d.name for d in targets) or "(no emulator folder found)"))
    for n in items:
        print("  +", n["name"])
    for p in problems:
        print("  ! skipped (invalid JSON) -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
