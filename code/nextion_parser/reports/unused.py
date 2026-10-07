"""HTML / CSV / JSON output of the unused-resources analysis."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from ..analysis.unused import analyze
from ..parser import Project
from .doc import Bullets, Card, Cards, Details, Doc, Heading, Para, Raw, Table, code, esc, render, tag


def _kb(n: int) -> str:
    return f"{n / 1024:.1f} KB" if n < 1048576 else f"{n / 1048576:.2f} MB"


EXTRA_CSS = """
.thumb{max-width:90px;max-height:60px;background:repeating-conic-gradient(#ccc 0 25%,#fff 0 50%) 0 0/12px 12px;border:1px solid var(--line)}
label{margin-right:12px}tr.hide{display:none}
"""
FILTER_JS = """<script>
const cb=document.getElementById('onlyun');
function f(){document.querySelectorAll('#imgs tr[class]').forEach(r=>r.classList.toggle('hide',cb.checked&&r.className.indexOf('unused')<0&&r.className.indexOf('uncertain')<0));}
cb.onchange=f;f();</script>"""


def build_doc(rep: dict, has_images: bool = True) -> Doc:
    """The unused-resources report as a document model (no HTML here)."""
    s = rep["summary"]
    b: list = [Para("Static analysis: it only finds what the component attributes and the <b>literal</b> references in the code show. "
                    "The .HMI file is not modified; deletion has to be done in the Nextion Editor "
                    "(image/font ids are the Editor's resource positions).", note=True),
               Cards([Card("Unused images", f"{s['images_unused']}/{s['images_total']}", f"estimated saving in the TFT: {_kb(s['images_unused_tft_bytes'])}"),
                      Card("Unused fonts", f"{s['fonts_unused']}/{s['fonts_total']}", _kb(s["fonts_unused_bytes"])),
                      Card("Unreferenced pages", str(s["pages_unreferenced"]),
                           f"no page reference to them; {s['pages_uncertain']} more uncertain (dynamic page or reachable from the MCU)"),
                      Card("Superfluous components", str(s["components_unused"]), "timer/variable/hotspot"),
                      Card(".HMI file", _kb(s["hmi_file_bytes"]),
                           f"of which deleted (dead) sections: {_kb(s['hmi_dead_bytes'])} – may disappear after \"Save as\" in the Editor")])]
    if s["dynamic_image_refs"] or s["dynamic_font_refs"]:
        b.append(Para(f"<b>Note:</b> the code contains {s['dynamic_image_refs']} dynamic image references and {s['dynamic_font_refs']} dynamic font references "
                      "(non-literal values). Affected items are classified as \"uncertain\" instead of \"unused\"."))
        b.append(Details("Dynamic references", [Bullets([code(x) for x in rep["dynamic"]["images"] + rep["dynamic"]["fonts"]])]))

    b.append(Heading("Images"))
    b.append(Raw("<p><label><input type='checkbox' id='onlyun' checked> only the unused ones</label></p>"))
    rows = []
    for x in rep["images"]:
        thumb = f"<img class='thumb' loading='lazy' src='img/{x['id']}.{x['format']}'>" if has_images else ""
        refs = "<br>".join(code(r) for r in x["refs"][:6]) + (f"<br>…+{len(x['refs']) - 6}" if len(x["refs"]) > 6 else "")
        rows.append([str(x["id"]), thumb, f"{x['width']}×{x['height']}", _kb(x["tft_bytes"]), tag(x["status"]), refs or "–"])
    b.append(Table(["ID", "Preview", "Size", "TFT (estimated)", "Status", "References"], rows, id="imgs",
                   row_classes=[x["status"] for x in rep["images"]]))
    b.append(Heading("Fonts"))
    b.append(Table(["ID", "Name", "Height", "Size", "Status", "References"], [
        [str(x["id"]), esc(x["name"]), f"{x['height']} px", _kb(x["bytes"]), tag(x["status"]), str(len(x["refs"]))] for x in rep["fonts"]]))
    b.append(Heading("Pages"))
    b.append(Table(["#", "Page", "Components", "Status", "Referenced from"], [
        [str(x["index"]), esc(x["name"]), str(x["components"]), tag(x["status"]),
         esc(", ".join(x["referenced_from"][:3])) or esc(x["note"])] for x in rep["pages"]]))
    b.append(Heading("Superfluous components"))
    if rep["components"]:
        b.append(Table(["Page", "Component", "Type", "Note"], [
            [esc(c["page"]), code(c["name"]), esc(c["type"]), esc(c["note"])] for c in rep["components"]]))
    else:
        b.append(Para("None.", note=True))
    b.append(Raw(FILTER_JS))
    return Doc(f"{rep['project']} – unused resources", b, EXTRA_CSS)


def write(project: Project, out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    (out / "img").mkdir(parents=True, exist_ok=True)
    for i, im in project.images.items():
        (out / "img" / f"{i}.{im.ext}").write_bytes(im.data)
    rep = analyze(project)
    paths = {"json": out / "unused.json", "html": out / "unused.html", "csv": out / "unused.csv"}
    paths["json"].write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    paths["html"].write_text(render(build_doc(rep)), encoding="utf-8")
    with paths["csv"].open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["kind", "id", "name", "status", "size_bytes", "details"])
        for x in rep["images"]:
            w.writerow(["image", x["id"], f"{x['width']}x{x['height']}", x["status"], x["tft_bytes"], "; ".join(x["refs"][:5])])
        for x in rep["fonts"]:
            w.writerow(["font", x["id"], x["name"], x["status"], x["bytes"], f"{len(x['refs'])} references"])
        for x in rep["pages"]:
            w.writerow(["page", x["index"], x["name"], x["status"], "", "; ".join(x["referenced_from"][:3])])
        for c in rep["components"]:
            w.writerow(["component", "", f"{c['page']}.{c['name']}", "unused", "", c["note"]])
    return paths
