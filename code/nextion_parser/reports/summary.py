"""Summary outputs: HTML summary report, navigation flowchart page, pages.json, navigation.mmd."""
from __future__ import annotations

import json
from pathlib import Path

from ..analysis.navigation import mermaid, navigation, pages_dict
from ..parser import Project
from .doc import Card, Cards, Doc, Heading, Para, Pre, Table, Bullets, code, esc, render


EXTRA_CSS = ".pill{display:inline-block;padding:1px 8px;margin:1px 2px 1px 0;border:1px solid var(--line);border-radius:10px;font-size:12px}"


def build_doc(project: Project) -> Doc:
    """The project summary as a document model (no HTML here)."""
    edges, dynamic = navigation(project)
    ncomp = sum(len(p.comps) for p in project.pages)
    out_deg: dict[str, dict[str, set]] = {}
    for (a, b), labels in edges.items():
        out_deg.setdefault(a, {})[b] = labels
    b: list = [Para("Detailed navigation diagram: <a href=\"navigation.html\" target=\"_blank\" rel=\"noopener\">navigation.html ↗</a> · raw data: <code>pages.json</code>", note=True),
               Cards([Card("Display", f"{project.width}×{project.height}", "px"), Card("Pages", str(len(project.pages)), "pages"),
                      Card("Components", str(ncomp), "total"), Card("Images", str(len(project.images)), "resources"),
                      Card("Fonts", str(len(project.fonts)), "resources"), Card("Start page", project.start_page or "unknown", "Program.s")])]
    if project.program:
        b += [Heading("Start-up program (Program.s)"), Pre(project.program.strip())]
    rows = []
    for p in project.pages:
        withcode = sum(1 for c in p.comps if any(c.code.values()))
        targets = "".join(f'<span class="pill">{esc(t)}</span>' for t in sorted(out_deg.get(p.name, {}))) or "–"
        rows.append([str(p.index), f"<b>{esc(p.name)}</b>", str(len(p.comps)), str(withcode), targets])
    b += [Heading("Pages"), Table(["#", "Page", "Components", "With event code", "Outgoing jumps"], rows),
          Heading("Navigation (by triggering component)"),
          Table(["From", "To", "Trigger event"], [[esc(a), esc(c), code(", ".join(sorted(labels)))] for (a, c), labels in edges.items()])]
    if dynamic:
        b.append(Para(f"Pages that jump via a variable (returning to the calling page): {code(', '.join(sorted(dynamic)))}", note=True))
    b.append(Heading("Warnings"))
    b.append(Bullets([esc(w) for w in project.warnings]) if project.warnings else Para("None.", note=True))
    return Doc(f"{project.name} – summary", b, EXTRA_CSS)


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
        "summary.html": render(build_doc(project)),
    }
    paths = []
    for name, text in files.items():
        p = out / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    return paths
