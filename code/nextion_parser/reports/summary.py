"""Summary outputs: HTML summary report, navigation flowchart page, pages.json, navigation.mmd."""
from __future__ import annotations

import html as _html
import json
from pathlib import Path

from ..analysis.navigation import mermaid, navigation, pages_dict
from ..parser import Project


def summary_html(project: Project) -> str:
    """Standalone HTML summary (same look as the other reports)."""
    e = _html.escape
    edges, dynamic = navigation(project)
    ncomp = sum(len(p.comps) for p in project.pages)
    out_deg: dict[str, dict[str, set]] = {}
    for (a, b), labels in edges.items():
        out_deg.setdefault(a, {})[b] = labels
    cards = [("Display", f"{project.width}×{project.height}", "px"), ("Pages", str(len(project.pages)), "pages"),
             ("Components", str(ncomp), "total"), ("Images", str(len(project.images)), "resources"),
             ("Fonts", str(len(project.fonts)), "resources"), ("Start page", project.start_page or "unknown", "Program.s")]
    h = [f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>{e(project.name)} – summary</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
:root{{--bg:#f4f5f7;--fg:#1c1f24;--card:#fff;--line:#d5d9e0;--mut:#667085;--ok:#15803d;--warn:#b45309;--acc:#1d4ed8}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14161a;--fg:#e6e8ec;--card:#1d2026;--line:#333842;--mut:#98a2b3;--ok:#4ade80;--warn:#fbbf24;--acc:#7ea6ff}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif;max-width:1100px;margin:auto}}
h1{{font-size:20px}}h2{{font-size:16px;margin-top:28px}}a{{color:var(--acc)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}}
.k{{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}}.v{{font-size:20px;font-weight:600;overflow-wrap:anywhere}}.s{{color:var(--mut);font-size:12px}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line)}}
th,td{{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-size:12px;color:var(--mut)}}
code,pre{{font:12px ui-monospace,monospace}}pre{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;overflow:auto;white-space:pre-wrap}}
.note{{color:var(--mut)}}.pill{{display:inline-block;padding:1px 8px;margin:1px 2px 1px 0;border:1px solid var(--line);border-radius:10px;font-size:12px}}
</style><body><h1>{e(project.name)} – summary</h1>
<p class="note">Detailed navigation diagram: <a href="navigation.html" target="_blank" rel="noopener">navigation.html ↗</a> · raw data: <code>pages.json</code></p>
<div class="grid">"""]
    for k, v, sub in cards:
        h.append(f'<div class="card"><div class="k">{e(k)}</div><div class="v">{e(v)}</div><div class="s">{e(sub)}</div></div>')
    h.append("</div>")
    if project.program:
        h.append(f"<h2>Start-up program (Program.s)</h2><pre>{e(project.program.strip())}</pre>")
    h.append("<h2>Pages</h2><table><tr><th>#</th><th>Page</th><th>Components</th><th>With event code</th><th>Outgoing jumps</th></tr>")
    for p in project.pages:
        withcode = sum(1 for c in p.comps if any(c.code.values()))
        targets = "".join(f'<span class="pill">{e(t)}</span>' for t in sorted(out_deg.get(p.name, {}))) or "–"
        h.append(f"<tr><td>{p.index}</td><td><b>{e(p.name)}</b></td><td>{len(p.comps)}</td><td>{withcode}</td><td>{targets}</td></tr>")
    h.append("</table><h2>Navigation (by triggering component)</h2><table><tr><th>From</th><th>To</th><th>Trigger event</th></tr>")
    for (a, b), labels in edges.items():
        h.append(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td><code>{e(', '.join(sorted(labels)))}</code></td></tr>")
    h.append("</table>")
    if dynamic:
        h.append(f"<p class='note'>Pages that jump via a variable (returning to the calling page): <code>{e(', '.join(sorted(dynamic)))}</code></p>")
    h.append("<h2>Warnings</h2>")
    h.append("<ul>" + "".join(f"<li>{e(w)}</li>" for w in project.warnings) + "</ul>" if project.warnings else "<p class='note'>None.</p>")
    h.append("</body></html>")
    return "".join(h)


def html(project: Project) -> str:
    return f"""<!doctype html><meta charset=utf-8><title>{project.name} – navigation</title>
<body style="font-family:sans-serif;margin:16px"><h2>{project.name} – page navigation</h2>
<pre class="mermaid">{mermaid(project)}</pre>
<script type="module">import m from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
m.initialize({{startOnLoad:true,flowchart:{{useMaxWidth:false}}}});</script>"""


def write_all(project: Project, out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "pages.json": json.dumps(pages_dict(project), ensure_ascii=False, indent=1),
        "navigation.mmd": mermaid(project),
        "navigation.html": html(project),
        "summary.html": summary_html(project),
    }
    paths = []
    for name, text in files.items():
        p = out / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    return paths
