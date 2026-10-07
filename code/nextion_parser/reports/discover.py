"""JSON output of the variable discovery."""
from __future__ import annotations

import json
from pathlib import Path

from ..analysis import discover
from ..parser import Project


def write(project: Project, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "variables.discovered.json"
    p.write_text(json.dumps({"project": project.name, "variables": discover.build(project)}, ensure_ascii=False, indent=1), encoding="utf-8")
    return p
