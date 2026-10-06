"""Updates scenarios.js from the scenarios/*.json files so that the emulator works from disk without any server.

Standard library only; runs anywhere Python 3 is installed (double-click update_scenarios.bat / .sh next to it).
Placement decides what it does:
  * <package>/update_scenarios.py   (next to index.html)  -> reads <package>/scenarios, writes <package>/scenarios.js
  * <output>/scripts/update_scenarios.py                  -> reads <output>/scenarios, writes scenarios.js into every
                                                             sibling folder that holds an emulator (emulator/, portable/)
This file is also copied into generated folders by nextion_parser.
"""
import json
import sys
from pathlib import Path

RESERVED = {"variables.json", "variables.discovered.json", "csv_profiles.json"}


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


def main() -> int:
    here = Path(__file__).resolve().parent
    if (here / "index.html").is_file():
        scen, targets = here / "scenarios", [here]
    else:
        scen = here.parent / "scenarios"
        targets = [d for d in sorted(here.parent.iterdir()) if (d / "index.html").is_file() and (d / "data.js").is_file()]
    scen.mkdir(exist_ok=True)
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
