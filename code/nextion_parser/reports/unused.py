"""HTML / CSV / JSON output of the unused-resources analysis."""
from __future__ import annotations

import csv
import html as _html
import json
from pathlib import Path

from ..analysis.unused import analyze
from ..parser import Project


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
