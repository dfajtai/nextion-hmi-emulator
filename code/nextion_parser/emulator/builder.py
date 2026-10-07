"""Generate a standalone, browser-based emulator from a parsed project.

Output: ``index.html`` + ``help.html`` + ``nextion_core.js`` + ``nextion_tools.js`` + ``i18n.js`` + ``data.js`` + ``img/``
(relative links; works from file:// as well). The portable (basic) variant has no help page and ships its own scenario tools.
"""
from __future__ import annotations

import json
import re
import shutil
from importlib import resources
from pathlib import Path

from ..analysis import discover, scenario
from ..parser import Project
from ..reports import help as helpdoc
from .model import EmulatorData, ReportLink, Screen
from .portable import PORTABLE_README, add_updater

# HTML reports found in the sibling folders after generation (links relative to the output folder);
# the GUI localizes the labels by key
REPORTS = [
    ("coverage", "../coverage/coverage.html"),
    ("unused", "../unused/unused.html"),
    ("navigation", "../summary/navigation.html"),
    ("summary", "../summary/summary.html"),
]
_SIZE = re.compile(r"^(\d{2,4})[xX×](\d{2,4})$")
ASSET_FILES = ("nextion_core.js", "nextion_tools.js", "i18n.js")


def parse_size(text: str) -> tuple[int, int]:
    m = _SIZE.match(text.strip())
    if not m:
        raise ValueError(f"Invalid size: {text!r} (expected format: 800x480)")
    return int(m.group(1)), int(m.group(2))


def assets():
    """The static front-end files shipped with the package."""
    return resources.files("nextion_parser.emulator").joinpath("assets")


class EmulatorBuilder:
    """Builds the emulator (data model + files) for one project."""

    def __init__(self, project: Project, *, start: str | None = None, screen: tuple[int, int] | None = None,
                 zoom: str | None = None, scenario_dir: str | Path | None = None, lang: str = "hu",
                 portable: bool = False):
        self.project, self.start, self.screen, self.zoom = project, start, screen, zoom
        self.scenario_dir = Path(scenario_dir) if scenario_dir else None
        self.lang, self.portable = lang if lang in ("hu", "en") else "hu", portable

    # ---- the data model
    def data(self) -> EmulatorData:
        p = self.project
        pages = []
        for pg in p.pages:
            page = dict(pg.page.attrs)
            page["code"] = pg.code
            pages.append({"index": pg.index, "name": pg.name, "page": page, "comps": [c.to_dict() for c in pg.comps]})
        w, h = self.screen or (p.width, p.height)
        start = self.start or p.start_page or p.pages[0].name
        if start not in {x["name"] for x in pages}:
            raise ValueError(f"Unknown start page: {start}")
        sdir = self.scenario_dir
        prof = sdir / "csv_profiles.json" if sdir else None
        scenarios = [] if self.portable else [
            s.to_dict() for s in scenario.load_dir(p, sdir) if not any("JSON" in i for i in s.issues)]
        return EmulatorData(
            pages=pages,
            picmap={str(i): f"img/{i}.{im.ext}" for i, im in p.images.items()},
            fonts={str(i): {"height": f.height, "name": f.name} for i, f in p.fonts.items()},
            screen=Screen(w, h, (p.width, p.height)), start=start, lang=self.lang,
            variables=discover.merge(discover.build(p), discover.load_overrides(sdir)),
            csv_profiles=json.loads(prof.read_text(encoding="utf-8")) if prof and prof.is_file() else {},
            scenarios=scenarios, portable=self.portable, zoom=self.zoom)

    # ---- the files
    def write(self, out_dir: str | Path) -> Path:
        """Write the emulator into `out_dir`; returns the path of index.html."""
        out = Path(out_dir)
        img = out / "img"
        if img.exists():                       # only delete the sub-folder we generated ourselves
            shutil.rmtree(img)
        img.mkdir(parents=True, exist_ok=True)
        for i, im in self.project.images.items():
            (img / f"{i}.{im.ext}").write_bytes(im.data)
        data = self.data()
        if not self.portable:
            data.reports = [ReportLink(k, href) for k, href in REPORTS if (out / href).resolve().is_file()]
        (out / "data.js").write_text(data.to_js(), encoding="utf-8")
        src = assets()
        for name in ASSET_FILES:
            (out / name).write_text(src.joinpath(name).read_text(encoding="utf-8"), encoding="utf-8")
        if self.portable:
            sc = out / "scenarios"
            sc.mkdir(exist_ok=True)
            (sc / "README.txt").write_text(PORTABLE_README, encoding="utf-8")
            add_updater(out, start_scripts=True)
            (out / "serve.py").write_text(
                resources.files("nextion_parser.emulator").joinpath("serve.py").read_text(encoding="utf-8"), encoding="utf-8")
        else:
            helpdoc.write(out, self.project, data.to_dict())
        sj = out / "scenarios.js"
        if not sj.exists():
            sj.write_text("window.NX_SCENARIOS=[];\n", encoding="utf-8")
        (out / "index.html").write_text(
            src.joinpath("emulator.html").read_text(encoding="utf-8").replace("__PROJECT__", self.project.name), encoding="utf-8")
        return out / "index.html"


def build_data(project: Project, start: str | None = None, screen: tuple[int, int] | None = None,
               zoom: str | None = None, scenario_dir: str | Path | None = None, lang: str = "hu",
               portable: bool = False) -> dict:
    """Convenience: the data model as a plain dict."""
    return EmulatorBuilder(project, start=start, screen=screen, zoom=zoom, scenario_dir=scenario_dir,
                           lang=lang, portable=portable).data().to_dict()


def generate(project: Project, out_dir: str | Path, start: str | None = None, screen: tuple[int, int] | None = None,
             zoom: str | None = None, scenario_dir: str | Path | None = None, lang: str = "hu",
             portable: bool = False) -> Path:
    """Convenience: build and write in one call."""
    return EmulatorBuilder(project, start=start, screen=screen, zoom=zoom, scenario_dir=scenario_dir,
                           lang=lang, portable=portable).write(out_dir)
