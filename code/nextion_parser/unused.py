"""Report of unused (unreferenced) resources, to help "compressing" the HMI.

The file is not modified (writing .HMI files is not supported); the report tells you what is worth deleting in the
Nextion Editor. The ids are the Editor's: image and font ids are positions in the main.HMI resource list.

What counts as a reference:
  * component attribute: ``pic``, ``pic2`` (image), ``font`` (font) - and the ``pic`` background of a page
  * code: literal assignments ``obj.pic=N``, ``obj.pic2=N``, ``obj.font=N``; the commands ``pic x,y,N`` /
    ``picq x,y,w,h,N`` / ``xpic dx,dy,w,h,sx,sy,N``; the font parameter of ``xstr``/``spstr``
  * a non-literal assignment (e.g. ``pbattery.pic=pic_index.val``) is *uncertain*: the images are then not
    necessarily unused
"""
from __future__ import annotations

import csv
import html as _html
import json
import re
from collections import defaultdict
from pathlib import Path

from . import codeutil, hmi
from .hmi import Project

_ASSIGN = re.compile(r"^([A-Za-z_][\w\.]*)\.(pic|pic2|bpic|ppic|font)\s*=\s*(.+)$")
NONE = 0xFFFF


def _lit(expr: str) -> int | None:
    expr = expr.strip()
    return int(expr) if re.fullmatch(r"\d+", expr) else None


def _split(s: str) -> list[str]:
    out, d, cur = [], 0, ""
    for ch in s:
        if ch in "([":
            d += 1
        elif ch in ")]":
            d -= 1
        if ch == "," and d == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return out


def _scan(project: Project) -> dict:
    img: dict[int, list[str]] = defaultdict(list)
    fnt: dict[int, list[str]] = defaultdict(list)
    dyn_img: list[str] = []
    dyn_font: list[str] = []
    page_targets: dict[str, list[str]] = defaultdict(list)
    names = {p.name for p in project.pages}
    for p in project.pages:
        for c in [p.page] + p.comps:
            for k in ("pic", "pic2", "bpic", "ppic"):
                v = c.attrs.get(k)
                if v is not None and v != NONE and c.type != 52:
                    img[v].append(f"{p.name}.{c.name}.{k}" if c.type != 121 else f"{p.name} (page background)")
            if "font" in c.attrs and c.type in (54, 59, 98, 116):
                fnt[c.attrs["font"]].append(f"{p.name}.{c.name}")
        for cname, code in [("(oldal)", p.code)] + [(c.name, c.code) for c in p.comps]:
            for ev, lines in code.items():
                where = f"{p.name}.{cname}.{ev}"
                for s in codeutil.statements(lines):
                    m = _ASSIGN.match(s)
                    if m:
                        n = _lit(m.group(3))
                        target = f"{where} → {m.group(1)}.{m.group(2)}"
                        if m.group(2) == "font":
                            (fnt[n].append(target) if n is not None else dyn_font.append(target))
                        else:
                            (img[n].append(target) if n is not None else dyn_img.append(f"{target}={m.group(3)}"))
                    m = re.match(r"^(pic|picq|xpic)\s+(.*)$", s)
                    if m:
                        a = _split(m.group(2))
                        n = _lit(a[-1])
                        (img[n].append(f"{where} → {m.group(1)}") if n is not None else dyn_img.append(f"{where} → {m.group(1)} {m.group(2)}"))
                    m = re.match(r"^(xstr|spstr)\s+(.*)$", s)
                    if m:
                        a = _split(m.group(2))
                        n = _lit(a[4]) if m.group(1) == "xstr" and len(a) > 4 else None
                        if n is not None:
                            fnt[n].append(f"{where} → xstr")
                    m = re.match(r"^page\s+(.+)$", s)
                    if m:
                        t = m.group(1).strip()
                        if t in names:
                            page_targets[t].append(where)
                        elif t.isdigit() and int(t) < len(project.pages):
                            page_targets[project.pages[int(t)].name].append(where)
                        else:
                            page_targets["*dynamic*"].append(where)
    return {"img": img, "font": fnt, "dyn_img": dyn_img, "dyn_font": dyn_font, "pages": page_targets}


def _section_sizes(path: Path) -> dict:
    """Section sizes from the directory: (kind, N) -> bytes (live records) + dead content."""
    d = path.read_bytes()
    live: dict[tuple[str, int], int] = defaultdict(int)
    dead = 0
    for e in hmi._directory(d):
        if e["deleted"] or e["raw0"] == 0:
            dead += e["size"]
            continue
        m = hmi._SECTION.match(e["name"])
        if m:
            live[(m.group(2), int(m.group(1)))] += e["size"]
    return {"live": dict(live), "dead_bytes": dead, "file_bytes": len(d)}


def _component_usage(project: Project) -> list[dict]:
    """Non-visual components (timer, variable, hotspot) that nothing refers to."""
    text = defaultdict(str)
    for p in project.pages:
        for code in [p.code] + [c.code for c in p.comps]:
            for lines in code.values():
                text[p.name] += "\n".join(lines) + "\n"
    all_text = "\n".join(text.values())
    out = []
    for p in project.pages:
        for c in p.comps:
            if c.type not in (51, 52, 109, 113):
                continue
            has_code = any(c.code.values())
            name = re.escape(c.name)
            local = re.search(rf"(?<![\w.]){name}(?![\w])", text[p.name]) is not None
            glob = re.search(rf"\b{re.escape(p.name)}\.{name}\b", all_text) is not None
            referenced = local or glob
            if c.type == 109 and has_code:
                continue
            if c.type == 51 and has_code:
                continue                                 # useful because of its timer code
            if not referenced and not has_code:
                out.append({"page": p.name, "name": c.name, "type": c.type_name,
                            "scope": "global" if c.attrs.get("vscope") == 1 else "local",
                            "note": ("global: the MCU may use it" if c.attrs.get("vscope") == 1 else "local and nothing refers to it")})
    return out


def analyze(project: Project) -> dict:
    scan = _scan(project)
    sizes = _section_sizes(project.path)
    uncertain_img = bool(scan["dyn_img"])
    uncertain_font = bool(scan["dyn_font"])

    images = []
    for i, im in sorted(project.images.items()):
        refs = scan["img"].get(i, [])
        images.append({"id": i, "width": im.width, "height": im.height, "format": im.ext, "refs": refs,
                       "tft_bytes": im.width * im.height * 2,
                       "status": "used" if refs else ("uncertain" if uncertain_img else "unused")})
    fonts = []
    for i, f in sorted(project.fonts.items()):
        refs = scan["font"].get(i, [])
        fonts.append({"id": i, "name": f.name, "height": f.height, "refs": refs, "bytes": f.size_bytes,
                      "status": "used" if refs else ("uncertain" if uncertain_font else "unused")})
    start = project.start_page
    pages = []
    for p in project.pages:
        t = scan["pages"].get(p.name, [])
        status = "used" if t or p.name == start else ("uncertain" if scan["pages"].get("*dynamic*") else "unreferenced")
        pages.append({"index": p.index, "name": p.name, "referenced_from": t[:5], "components": len(p.comps),
                      "status": status,
                      "note": "" if status == "used" else "no `page` reference in the HMI code; the MCU may still reach it with a serial `page` command"})
    comps = _component_usage(project)
    unused_img = [x for x in images if x["status"] == "unused"]
    unused_fnt = [x for x in fonts if x["status"] == "unused"]
    summary = {
        "images_total": len(images), "images_unused": len(unused_img),
        "images_unused_tft_bytes": sum(x["tft_bytes"] for x in unused_img),
        "images_tft_bytes": sum(x["tft_bytes"] for x in images),
        "fonts_total": len(fonts), "fonts_unused": len(unused_fnt), "fonts_unused_bytes": sum(x["bytes"] for x in unused_fnt),
        "pages_unreferenced": sum(1 for x in pages if x["status"] == "unreferenced"),
        "pages_uncertain": sum(1 for x in pages if x["status"] == "uncertain"),
        "components_unused": len(comps),
        "hmi_file_bytes": sizes["file_bytes"], "hmi_dead_bytes": sizes["dead_bytes"],
        "dynamic_image_refs": len(scan["dyn_img"]), "dynamic_font_refs": len(scan["dyn_font"]),
    }
    return {"project": project.name, "summary": summary, "images": images, "fonts": fonts, "pages": pages,
            "components": comps, "dynamic": {"images": scan["dyn_img"], "fonts": scan["dyn_font"]}}


def _kb(n: int) -> str:
    return f"{n / 1024:.1f} KB" if n < 1048576 else f"{n / 1048576:.2f} MB"


def render_html(rep: dict, has_images: bool = True) -> str:
    e = _html.escape
    s = rep["summary"]
    h = [f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>{e(rep['project'])} – unused resources</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
:root{{--bg:#f4f5f7;--fg:#1c1f24;--card:#fff;--line:#d5d9e0;--mut:#667085;--ok:#15803d;--warn:#b45309;--bad:#b91c1c}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14161a;--fg:#e6e8ec;--card:#1d2026;--line:#333842;--mut:#98a2b3;--ok:#4ade80;--warn:#fbbf24;--bad:#f87171}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif;max-width:1100px;margin:auto}}
h1{{font-size:20px}}h2{{font-size:16px;margin-top:28px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}}
.k{{color:var(--mut);font-size:12px;text-transform:uppercase}}.v{{font-size:26px;font-weight:600}}.s{{color:var(--mut);font-size:12px}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line)}}
th,td{{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-size:12px;color:var(--mut)}}
.tag{{padding:1px 8px;border-radius:10px;font-size:12px;color:#fff}}.used{{background:var(--ok)}}.unused,.unreferenced{{background:var(--bad)}}.uncertain{{background:var(--warn)}}
.thumb{{max-width:90px;max-height:60px;background:repeating-conic-gradient(#ccc 0 25%,#fff 0 50%) 0 0/12px 12px;border:1px solid var(--line)}}
code{{font:12px ui-monospace,monospace}}.note{{color:var(--mut)}}label{{margin-right:12px}}
tr.hide{{display:none}}
</style><body><h1>{e(rep['project'])} – unused resources</h1>
<p class="note">Static analysis: it only finds what the component attributes and the <b>literal</b> references in the code show.
The .HMI file is not modified; deletion has to be done in the Nextion Editor (image/font ids are the Editor's resource positions).</p>
<div class="grid">
<div class="card"><div class="k">Unused images</div><div class="v">{s['images_unused']}/{s['images_total']}</div><div class="s">estimated saving in the TFT: {_kb(s['images_unused_tft_bytes'])}</div></div>
<div class="card"><div class="k">Unused fonts</div><div class="v">{s['fonts_unused']}/{s['fonts_total']}</div><div class="s">{_kb(s['fonts_unused_bytes'])}</div></div>
<div class="card"><div class="k">Unreferenced pages</div><div class="v">{s['pages_unreferenced']}</div><div class="s">no page reference to them; {s['pages_uncertain']} more uncertain (dynamic page or reachable from the MCU)</div></div>
<div class="card"><div class="k">Superfluous components</div><div class="v">{s['components_unused']}</div><div class="s">timer/variable/hotspot</div></div>
<div class="card"><div class="k">.HMI file</div><div class="v">{_kb(s['hmi_file_bytes'])}</div><div class="s">of which deleted (dead) sections: {_kb(s['hmi_dead_bytes'])} – may disappear after "Save as" in the Editor</div></div>
</div>"""]
    if s["dynamic_image_refs"] or s["dynamic_font_refs"]:
        h.append(f"<p><b>Note:</b> the code contains {s['dynamic_image_refs']} dynamic image references and {s['dynamic_font_refs']} dynamic font references "
                 "(non-literal values). Affected items are classified as \"uncertain\" instead of \"unused\".</p>")
        h.append("<details><summary>Dynamic references</summary><ul>" + "".join(f"<li><code>{e(x)}</code></li>" for x in rep["dynamic"]["images"] + rep["dynamic"]["fonts"]) + "</ul></details>")

    h.append("<h2>Images</h2><p><label><input type='checkbox' id='onlyun' checked> only the unused ones</label></p>"
             "<table id='imgs'><tr><th>ID</th><th>Preview</th><th>Size</th><th>TFT (estimated)</th><th>Status</th><th>References</th></tr>")
    for x in rep["images"]:
        thumb = f"<img class='thumb' loading='lazy' src='img/{x['id']}.{x['format']}'>" if has_images else ""
        refs = "<br>".join(f"<code>{e(r)}</code>" for r in x["refs"][:6]) + (f"<br>…+{len(x['refs']) - 6}" if len(x["refs"]) > 6 else "")
        h.append(f"<tr class='{x['status']}'><td>{x['id']}</td><td>{thumb}</td><td>{x['width']}×{x['height']}</td><td>{_kb(x['tft_bytes'])}</td>"
                 f"<td><span class='tag {x['status']}'>{x['status']}</span></td><td>{refs or '–'}</td></tr>")
    h.append("</table>")
    h.append("<h2>Fonts</h2><table><tr><th>ID</th><th>Name</th><th>Height</th><th>Size</th><th>Status</th><th>References</th></tr>")
    for x in rep["fonts"]:
        h.append(f"<tr><td>{x['id']}</td><td>{e(x['name'])}</td><td>{x['height']} px</td><td>{_kb(x['bytes'])}</td>"
                 f"<td><span class='tag {x['status']}'>{x['status']}</span></td><td>{len(x['refs'])}</td></tr>")
    h.append("</table><h2>Pages</h2><table><tr><th>#</th><th>Page</th><th>Components</th><th>Status</th><th>Referenced from</th></tr>")
    for x in rep["pages"]:
        h.append(f"<tr><td>{x['index']}</td><td>{e(x['name'])}</td><td>{x['components']}</td><td><span class='tag {x['status']}'>{x['status']}</span></td>"
                 f"<td>{e(', '.join(x['referenced_from'][:3])) or e(x['note'])}</td></tr>")
    h.append("</table><h2>Superfluous components</h2>")
    if rep["components"]:
        h.append("<table><tr><th>Page</th><th>Component</th><th>Type</th><th>Note</th></tr>" + "".join(
            f"<tr><td>{e(c['page'])}</td><td><code>{e(c['name'])}</code></td><td>{e(c['type'])}</td><td>{e(c['note'])}</td></tr>" for c in rep["components"]) + "</table>")
    else:
        h.append("<p class='note'>None.</p>")
    h.append("""<script>
const cb=document.getElementById('onlyun');
function f(){document.querySelectorAll('#imgs tr[class]').forEach(r=>r.classList.toggle('hide',cb.checked&&r.className.indexOf('unused')<0&&r.className.indexOf('uncertain')<0));}
cb.onchange=f;f();</script></body></html>""")
    return "".join(h)


def write(project: Project, out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    (out / "img").mkdir(parents=True, exist_ok=True)
    for i, im in project.images.items():
        (out / "img" / f"{i}.{im.ext}").write_bytes(im.data)
    rep = analyze(project)
    paths = {"json": out / "unused.json", "html": out / "unused.html", "csv": out / "unused.csv"}
    paths["json"].write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    paths["html"].write_text(render_html(rep), encoding="utf-8")
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
