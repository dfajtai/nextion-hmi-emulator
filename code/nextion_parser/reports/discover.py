"""JSON output of the variable discovery (the list itself plus editable templates for variables.json / csv_profiles.json)."""
from __future__ import annotations

import json
from pathlib import Path

from ..analysis import discover
from ..analysis.csvprofile import guess_profile
from ..parser import Project


def _dump(path: Path, obj) -> Path:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def write(project: Project, out_dir: Path) -> list[Path]:
    """Write variables.discovered.json (always), variables.template.json and, when a statistics page is recognized,
    csv_profiles.template.json. The templates are skeletons to copy into the scenarios folder and edit; they never overwrite
    the real files. Returns the written paths (the discovered list first)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    found = discover.build(project)
    paths = [_dump(out_dir / "variables.discovered.json", {"project": project.name, "variables": found}),
             _dump(out_dir / "variables.template.json", discover.variables_template(found))]
    prof = guess_profile(project)
    stale = out_dir / "csv_profiles.template.json"
    if prof:
        paths.append(_dump(stale, prof))
    elif stale.exists():
        stale.unlink()
    return paths
