"""Headless runtime smoke test: runs every event of every page of the project in Node against the emulator core."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from ..parser import Project
from .builder import EmulatorBuilder, assets


def runtime(project: Project, workdir: Path | None = None, scenario_dir: Path | None = None) -> dict:
    node = shutil.which("node")
    if not node:
        return {"available": False, "reason": "`node` was not found on the PATH; the runtime smoke test is skipped"}
    tmp = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="nxcov_"))
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "data.js").write_text(EmulatorBuilder(project, scenario_dir=scenario_dir).data().to_js(), encoding="utf-8")
    tpl = assets()
    (tmp / "nextion_core.js").write_text(tpl.joinpath("nextion_core.js").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp / "smoke.js").write_text(tpl.joinpath("smoke.js").read_text(encoding="utf-8"), encoding="utf-8")
    try:
        r = subprocess.run([node, "smoke.js", "data.js", "nextion_core.js"], cwd=tmp, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return {"available": False, "reason": "the smoke test was aborted because of a timeout"}
    if r.returncode != 0:
        return {"available": False, "reason": "the smoke test failed: " + r.stderr.strip()[:500]}
    raw = json.loads(r.stdout)
    res = raw["results"]
    by = Counter(x["status"] for x in res)
    total = len(res)
    good = by["ok"] + by["redirect"]
    return {
        "available": True, "events": total, "by_status": dict(by),
        "percent": round(100 * good / total, 1) if total else 100.0,
        "problems": [x for x in res if x["status"] not in ("ok", "redirect")],
        "reachable": raw["reachable"], "unreachable": raw["unreachable"],
        "reachable_percent": round(100 * len(raw["reachable"]) / len(project.pages), 1) if project.pages else 0.0,
        "transitions": raw["transitions"], "scenario_runs": raw.get("scenarios", []),
    }


