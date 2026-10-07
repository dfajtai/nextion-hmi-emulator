"""Loading and static validation of simulation scenarios.

A scenario is a JSON file (or a ``{"scenarios": [...]}`` list):

    {
      "name": {"hu": "Példa", "en": "Example"},     // text or {"hu": ..., "en": ...}
      "description": "What does the display show when the value is 12?",
      "page": "pageA",                  // optional: start page (default: the project start page)
      "steps": [
        {"say": {"hu": "Az MCU 12-re állítja", "en": "The MCU sets it to 12"}},
        {"set": {"pageA.level.val": 12, "pageA.count.val": 1520}},
        {"wait": 1500},
        {"cmd": "page pageB"},          // raw Nextion instruction, as the MCU would send it
        {"click": "btnStart"},                     // button press on the current page (down + up)
        {"goto": "pageB"},
        {"ramp": {"ref": "pageA.level.val", "from": 10, "to": 100, "step": 5, "every": 300}},
        {"wave": {"ref": "pageB.wave0", "ch": 0, "fn": "sine", "n": 300, "min": 40, "max": 200, "noise": 0.1}},
        {"repeat": 3, "steps": [ ... ]}
      ]
    }

``variables.json`` (optional, hand-edited) refines the discovered variables:
``{"pageA.level.val": {"label": {"hu": "Szint", "en": "Level"}, "unit": "%",
"min": 0, "max": 100, "group": "Inputs"}}``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..parser import Project

RESERVED = {"variables.json", "variables.discovered.json", "variables.template.json", "csv_profiles.json", "csv_profiles.template.json"}
STEP_KEYS = {"set", "cmd", "click", "goto", "wait", "say", "ramp", "repeat", "steps", "wave"}


@dataclass
class Scenario:
    id: str
    name: object                 # str or {"hu": ..., "en": ...}
    description: object
    page: str | None
    steps: list
    source: str
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "description": self.description, "page": self.page, "steps": self.steps}


def validate(project: Project, scn: Scenario, start: str) -> list[str]:
    issues: list[str] = []
    comps = {p.name: {c.name for c in p.comps} | {"@page"} for p in project.pages}
    cur = scn.page or start
    if cur not in comps:
        issues.append(f"unknown start page: {cur}")
        return issues

    def check_ref(ref: str, page: str | None):
        parts = ref.split(".")
        if len(parts) == 3:
            if parts[0] not in comps or parts[1] not in comps[parts[0]]:
                issues.append(f"unknown reference: {ref}")
        elif len(parts) == 2:
            if page is None:
                return               # the current page is not known statically
            if parts[0] not in comps[page]:
                issues.append(f"{ref}: no such component on page {page} (use the full form: page.component.attribute)")
        else:
            issues.append(f"malformed reference: {ref}")

    def walk(steps: list, page: str | None) -> str | None:
        for st in steps:
            if not isinstance(st, dict):
                issues.append(f"step is not an object: {st!r}")
                continue
            for k in st:
                if k not in STEP_KEYS:
                    issues.append(f"unknown step key: {k}")
            if "goto" in st:
                if st["goto"] in comps:
                    page = st["goto"]
                else:
                    issues.append(f"unknown page: {st['goto']}")
            if "cmd" in st:
                for line in st["cmd"] if isinstance(st["cmd"], list) else [st["cmd"]]:
                    if line.strip().startswith("page "):
                        t = line.strip()[5:].strip()
                        if t in comps:
                            page = t
            if "click" in st:
                if page is not None and st["click"] not in comps.get(page, set()):
                    issues.append(f"click: no component '{st['click']}' on page {page}")
                page = None          # a button press may change the page: it is not known statically from here on
            for ref in ([k for k in st["set"]] if isinstance(st.get("set"), dict) else []):
                check_ref(ref, page)
            if isinstance(st.get("ramp"), dict) and "ref" in st["ramp"]:
                check_ref(st["ramp"]["ref"], page)
            if isinstance(st.get("wave"), dict):
                w = st["wave"]
                parts = str(w.get("ref", "")).split(".")
                ok = (len(parts) == 2 and parts[0] in comps and parts[1] in comps[parts[0]]) or \
                     (len(parts) == 1 and (page is None or parts[0] in comps.get(page, set())))
                if not ok:
                    issues.append(f"wave: unknown waveform: {w.get('ref')}")
            if "wait" in st and not isinstance(st["wait"], (int, float)):
                issues.append("the value of wait is not a number")
            if "steps" in st:
                page = walk(st["steps"], page)
        return page

    walk(scn.steps, cur)
    return issues


def load_dir(project: Project, directory: Path | None) -> list[Scenario]:
    if not directory or not Path(directory).is_dir():
        return []
    out: list[Scenario] = []
    start = project.start_page or project.pages[0].name
    for f in sorted(Path(directory).glob("*.json")):
        if f.name in RESERVED:
            continue
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            out.append(Scenario(f.stem, f.stem, "", None, [], f.name, [f"invalid JSON: {e}"]))
            continue
        items = raw["scenarios"] if isinstance(raw, dict) and "scenarios" in raw else [raw]
        for i, it in enumerate(items):
            sid = f.stem if len(items) == 1 else f"{f.stem}-{i + 1}"
            s = Scenario(sid, it.get("name", sid), it.get("description", ""), it.get("page"), it.get("steps", []), f.name)
            s.issues = validate(project, s, start)
            out.append(s)
    return out
