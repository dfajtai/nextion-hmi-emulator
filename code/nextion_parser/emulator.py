"""Generate a standalone, browser-based emulator from a Project.

Output: ``index.html`` + ``help.html`` + ``nextion_core.js`` + ``nextion_tools.js`` + ``i18n.js`` + ``data.js`` + ``img/``
(relative links; works from file:// as well).
"""
from __future__ import annotations

import json
import re
import shutil
from importlib import resources
from pathlib import Path

from . import discover, helpdoc, scenario
from .hmi import Project

# HTML reports found in the sibling folders after generation (links relative to the output folder);
# the GUI localizes the labels by key
REPORTS = [
    ("coverage", "../coverage/coverage.html"),
    ("unused", "../unused/unused.html"),
    ("navigation", "../summary/navigation.html"),
    ("summary", "../summary/summary.html"),
]
_SIZE = re.compile(r"^(\d{2,4})[xX×](\d{2,4})$")


PORTABLE_README = """Scenarios folder / Forgatókönyvek mappája
==========================================
EN: Put the scenario .json files recorded in the expert emulator here. In index.html press "Open folder..."
    and choose this folder (or drag the files onto the page). Files other than .json are ignored.
    Optional: run `python3 start.py --open` in the package folder - then the scenarios of this folder load automatically.
HU: Az expert emulátorban rögzített forgatókönyv .json fájlokat ide másold. Az index.html-ben a
    "Mappa megnyitása..." gombbal válaszd ki ezt a mappát (vagy húzd a fájlokat az oldalra).
    Opcionális: `python3 start.py --open` a csomag mappájában - ekkor a mappa forgatókönyvei automatikusan betöltődnek.
"""


def parse_size(text: str) -> tuple[int, int]:
    m = _SIZE.match(text.strip())
    if not m:
        raise ValueError(f"Invalid size: {text!r} (expected format: 800x480)")
    return int(m.group(1)), int(m.group(2))


def build_data(project: Project, start: str | None = None, screen: tuple[int, int] | None = None,
               zoom: str | None = None, scenario_dir: str | Path | None = None, lang: str = "hu",
               portable: bool = False) -> dict:
    pages = []
    for p in project.pages:
        page = dict(p.page.attrs)
        page["code"] = p.code
        pages.append({"index": p.index, "name": p.name, "page": page, "comps": [c.to_dict() for c in p.comps]})
    w, h = screen or (project.width, project.height)
    data = {
        "pages": pages,
        "picmap": {str(i): f"img/{i}.{im.ext}" for i, im in project.images.items()},
        "fonts": {str(i): {"height": f.height, "name": f.name} for i, f in project.fonts.items()},
        "screen": {"w": w, "h": h, "native": [project.width, project.height]},
        "start": start or project.start_page or project.pages[0].name,
        "lang": lang if lang in ("hu", "en") else "hu",      # default GUI language (the user can switch at run time)
    }
    sdir = Path(scenario_dir) if scenario_dir else None
    data["variables"] = discover.merge(discover.build(project), discover.load_overrides(sdir))
    prof = sdir / "csv_profiles.json" if sdir else None
    data["csvProfiles"] = json.loads(prof.read_text(encoding="utf-8")) if prof and prof.is_file() else {}
    data["scenarios"] = [s.to_dict() for s in scenario.load_dir(project, sdir) if not any("JSON" in i for i in s.issues)]
    data["reports"] = []
    if portable:                                  # basic variant: no built-in scenarios, locked to simple mode
        data["portable"] = True
        data["scenarios"] = []
    if zoom:
        data["zoom"] = zoom
    if data["start"] not in {p["name"] for p in pages}:
        raise ValueError(f"Unknown start page: {data['start']}")
    return data


def generate(project: Project, out_dir: str | Path, start: str | None = None,
             screen: tuple[int, int] | None = None, zoom: str | None = None,
             scenario_dir: str | Path | None = None, lang: str = "hu",
             portable: bool = False) -> Path:
    out = Path(out_dir)
    img = out / "img"
    if img.exists():                       # only delete the sub-folder we generated ourselves
        shutil.rmtree(img)
    img.mkdir(parents=True, exist_ok=True)
    for i, im in project.images.items():
        (img / f"{i}.{im.ext}").write_bytes(im.data)
    data = build_data(project, start, screen, zoom, scenario_dir, lang, portable)
    if not portable:
        data["reports"] = [{"key": key, "href": href} for key, href in REPORTS if (out / href).resolve().is_file()]
    (out / "data.js").write_text("const DATA=" + json.dumps(data, ensure_ascii=False) + ";", encoding="utf-8")
    tpl = resources.files("nextion_parser").joinpath("templates")
    (out / "nextion_core.js").write_text(tpl.joinpath("nextion_core.js").read_text(encoding="utf-8"), encoding="utf-8")
    (out / "nextion_tools.js").write_text(tpl.joinpath("nextion_tools.js").read_text(encoding="utf-8"), encoding="utf-8")
    (out / "i18n.js").write_text(tpl.joinpath("i18n.js").read_text(encoding="utf-8"), encoding="utf-8")
    if portable:
        sc = out / "scenarios"
        sc.mkdir(exist_ok=True)
        (sc / "README.txt").write_text(PORTABLE_README, encoding="utf-8")
        add_updater(out)
        (out / "start.py").write_text(resources.files("nextion_parser").joinpath("serve.py").read_text(encoding="utf-8"),
                                      encoding="utf-8")
    else:
        helpdoc.write(out, project, data)
    sj = out / "scenarios.js"
    if not sj.exists():
        sj.write_text("window.NX_SCENARIOS=[];\n", encoding="utf-8")
    (out / "index.html").write_text(
        tpl.joinpath("emulator.html").read_text(encoding="utf-8").replace("__PROJECT__", project.name), encoding="utf-8")
    return out / "index.html"


LAUNCHER_LINKS = [
    ("Emulator (expert)", "emulator/index.html", "full emulator: macro recorder, variables, CSV, reports"),
    ("Emulator (basic, portable)", "portable/index.html", "simple mode only, scenarios from the scenarios/ folder"),
    ("Coverage report", "coverage/coverage.html", ""),
    ("Unused resources", "unused/unused.html", ""),
    ("Navigation diagram", "summary/navigation.html", ""),
    ("Summary", "summary/summary.html", ""),
]


def write_launcher(root: str | Path, project_name: str) -> Path:
    """Write <root>/index.html: one page linking every generated part (the files must exist)."""
    root = Path(root)
    rows = "".join(
        f'<li><a href="{href}">{title}</a>' + (f" <span>{note}</span>" if note else "") + "</li>"
        for title, href, note in LAUNCHER_LINKS if (root / href).is_file())
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{project_name}</title><style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;color:#111827;background:#f9fafb}}
@media(prefers-color-scheme:dark){{body{{color:#e5e7eb;background:#111827}}a{{color:#93c5fd}}code{{background:#1f2937}}}}
h1{{font-size:22px}}li{{margin:8px 0}}li span,p{{color:#6b7280;font-size:14px}}code{{background:#e5e7eb;padding:1px 5px;border-radius:4px}}
</style></head><body><h1>{project_name}</h1><ul>{rows}</ul>
<p><b>Without a server</b> (just open the pages): put scenario <code>.json</code> files into the <code>scenarios/</code> folder, then
run <code>scripts/update_scenarios.bat</code> (Windows) or <code>scripts/update_scenarios.sh</code> (Linux/macOS; needs Python 3).
It refreshes <code>scenarios.js</code> in the emulator folders – reload the page and the scenarios are there.<br>
<b>With the helper server</b>: <code>./code/setup_and_run.sh serve output/{project_name}</code> – recordings made in the expert
emulator are saved into <code>scenarios/</code> and appear in the basic emulator automatically.</p></body></html>"""
    out = root / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def add_updater(folder: Path) -> None:
    """Copy update_scenarios.py + double-click wrappers into `folder`."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    src = resources.files("nextion_parser").joinpath("update_scenarios.py").read_text(encoding="utf-8")
    (folder / "update_scenarios.py").write_text(src, encoding="utf-8")
    (folder / "update_scenarios.bat").write_bytes(
        b'@echo off\r\npy -3 "%~dp0update_scenarios.py" || python "%~dp0update_scenarios.py"\r\npause\r\n')
    sh = folder / "update_scenarios.sh"
    sh.write_text('#!/bin/sh\ncd "$(dirname "$0")" && python3 update_scenarios.py\n', encoding="utf-8")
    sh.chmod(0o755)


def write_scripts(root: str | Path) -> Path:
    """<root>/scripts/ (scenario updater for the whole output folder) and the shared <root>/scenarios/ folder."""
    root = Path(root)
    add_updater(root / "scripts")
    (root / "scenarios").mkdir(exist_ok=True)
    (root / "scenarios" / "README.txt").write_text(PORTABLE_README, encoding="utf-8")
    return root / "scripts"
