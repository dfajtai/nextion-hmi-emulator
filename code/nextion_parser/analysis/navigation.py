"""Page navigation analysis: which page jumps where (edges), Mermaid flowchart, pages/components dictionary."""
from __future__ import annotations

import re
from collections import OrderedDict

from ..parser import Project

_PAGE_CMD = re.compile(r"\bpage\s+([A-Za-z_0-9\.\[\]]+)")
_STYLE = {
    "main": "fill:#dbeafe,stroke:#1d4ed8,color:#000",
    "cal": "fill:#fef3c7,stroke:#b45309,color:#000",
    "exp": "fill:#dcfce7,stroke:#15803d,color:#000",
    "set": "fill:#f3e8ff,stroke:#7e22ce,color:#000",
    "keyb": "fill:#e5e7eb,stroke:#4b5563,color:#000",
    "dyn": "fill:#fff,stroke:#999,stroke-dasharray:4 3,color:#000",
}


def _category(name: str) -> str:
    n = name.lower()
    if n.startswith("keyb"):
        return "keyb"
    if "cal" in n or n.endswith("wait") or "weighterr" in n:
        return "cal"
    if n.startswith(("pagee", "pageexport")):
        return "exp"
    if "setting" in n:
        return "set"
    return "main"


def navigation(project: Project) -> tuple[OrderedDict, set[str]]:
    """Return ({(source, target): {triggering component.event}}, pages that jump via a variable)."""
    names = {p.name for p in project.pages}
    edges: OrderedDict = OrderedDict()
    dynamic: set[str] = set()
    for p in project.pages:
        sources = [("page", p.code)] + [(c.name, c.code) for c in p.comps]
        for cname, code in sources:
            for ev, lines in code.items():
                for line in lines:
                    if line.strip().startswith("//"):
                        continue
                    for m in _PAGE_CMD.finditer(line):
                        t = m.group(1)
                        label = f"{cname}.{ev}" if cname != "page" else f"auto@{ev}"
                        if t in names:
                            edges.setdefault((p.name, t), set()).add(label)
                        elif "[" in t or "." in t:
                            dynamic.add(p.name)
    return edges, dynamic


def mermaid(project: Project) -> str:
    edges, dynamic = navigation(project)
    out = ["flowchart LR"]
    for p in project.pages:
        out.append(f'  {p.name}["{p.name}"]:::{_category(p.name)}')
    if dynamic:
        out.append('  CALLER(["calling page<br/>(from a variable)"]):::dyn')
    for (a, b), labels in edges.items():
        out.append(f'  {a} -->|"{", ".join(sorted(labels))}"| {b}')
    for a in sorted(dynamic):
        out.append(f'  {a} -.->|"back"| CALLER')
    out += [f"  classDef {k} {v}" for k, v in _STYLE.items()]
    return "\n".join(out)


def pages_dict(project: Project) -> dict:
    return {
        "project": project.name,
        "screen": {"width": project.width, "height": project.height},
        "start_page": project.start_page,
        "program": project.program,
        "warnings": project.warnings,
        "pages": [
            {"name": p.name, "code": p.code, "components": [c.to_dict() for c in p.comps]}
            for p in project.pages
        ],
    }
