"""Simulator coverage report produced after the conversion: coverage.json + coverage.html.

Three layers:
  1. structure  - what could be read from the file (pages, object counts, images, fonts)
  2. static     - does the emulator support the component types, attributes and commands
  3. runtime (Node) - does the emulator core really run every event of every page
The static support tables mirror the behaviour of ``emulator/assets/nextion_core.js`` / ``emulator.html``;
the tests make sure they do not drift apart.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from ..i18n import loc
from ..parser import TYPE_NAMES, Project
from ..parser.codeutil import statements as _statements
from . import discover, scenario, unused

SOURCES = [
    ("newmatik/nextion-hmi-writer – byte-level .HMI format description", "https://github.com/newmatik/nextion-hmi-writer"),
    ("UNUF/nxt-doc – Nextion file formats", "https://github.com/UNUF/nxt-doc"),
    ("Nextion Instruction Set", "https://nextion.tech/instruction-set/"),
]

# component type -> (support level, note)
TYPE_SUPPORT = {
    121: ("full", "page: background colour/image, events"),
    98: ("full", "button: colour/image, pressed state, text"),
    116: ("full", "text"),
    54: ("full", "number"),
    59: ("full", "decimal number (xfloat)"),
    112: ("full", "picture"),
    1: ("partial", "slider: only the fill is drawn, not draggable"),
    106: ("partial", "progress bar: simple fill"),
    0: ("partial", "waveform: grid + data series (add/cle, scenario wave step); no scrolling/addt"),
    56: ("partial", "checkbox: state is not clickable"),
    57: ("partial", "radio button: state is not clickable"),
    109: ("full", "hotspot: invisible, handles events"),
    51: ("full", "timer (tim/en/timer event)"),
    52: ("full", "variable (val/txt)"),
}
# attributes actually used by the renderer / interpreter
USED_ATTRS = {
    "type", "id", "objname", "vscope", "x", "y", "w", "h", "sta", "bco", "bco2", "pco", "pco2", "pic", "pic2",
    "txt", "val", "font", "xcen", "ycen", "isbr", "minval", "maxval", "lenth", "vvs1", "en", "tim",
}
# commands handled by the interpreter
SUPPORTED_CMDS = {"page", "int", "covx", "cov", "substr", "btlen", "strlen", "wepo", "repo",
                  "printh", "prints", "print", "click", "vis", "add", "cle"}
IGNORED_CMDS = {"delay", "tsw", "ref", "get", "rest", "sleep", "thsp", "thup", "bkcmd", "doevents", "addt"}
_CMD = re.compile(r"^([A-Za-z_]+)\b")
_STRUCT_ATTRS = {"aph", "movex", "movey", "endx", "endy", "effect", "first", "time", "lockobj", "groupid0", "groupid1",
                 "drag", "sendkey", "up", "down", "left", "right"}


# ---------------------------------------------------------------- static: code
def classify(stmt: str) -> tuple[str, str]:
    """Return (status, command): supported | ignored | unknown."""
    s = stmt
    m = re.match(r"^(if|while|for)\s*\(", s)
    if m:
        rest = re.sub(r"^(if|while|for)\s*\(.*\)\s*", "", s) if m.group(1) == "if" else ""
        return ("supported", m.group(1)) if not rest else classify(rest)
    if re.match(r"^else\b", s):
        rest = re.sub(r"^else\s*", "", s)
        return ("supported", "else") if not rest else classify(rest)
    m = _CMD.match(s)
    word = m.group(1) if m else ""
    if word in SUPPORTED_CMDS and not re.match(rf"^{word}\s*(=|\+=|-=)", s):
        return "supported", word
    if word in IGNORED_CMDS:
        return "ignored", word
    if re.match(r"^.+?(\+\+|--)$", s):
        return "supported", "incdec"
    if re.match(r"^[A-Za-z_][\w\[\]\.]*?\s*(\+=|-=|\*=|\/=|=)\s*.+$", s):
        return "supported", "assign"
    return "unknown", word or s[:20]


def _code_sources(project: Project):
    for p in project.pages:
        yield p.name, "(page)", p.code
        for c in p.comps:
            yield p.name, c.name, c.code
    if project.program:
        yield "Program.s", "(startup)", {"startup": project.program.splitlines()}


def static_code(project: Project) -> dict:
    kinds: Counter = Counter()
    status: Counter = Counter()
    unknown: dict[str, list] = defaultdict(list)
    ignored: dict[str, int] = Counter()
    for page, comp, code in _code_sources(project):
        for ev, lines in code.items():
            for s in _statements(lines):
                st, kind = classify(s)
                status[st] += 1
                kinds[kind] += 1
                if st == "unknown":
                    unknown[kind].append({"where": f"{page}.{comp}.{ev}", "line": s})
                elif st == "ignored":
                    ignored[kind] += 1
    total = sum(status.values())
    ok = status["supported"] + status["ignored"]
    return {
        "total": total, "supported": status["supported"], "ignored": status["ignored"], "unknown": status["unknown"],
        "percent": round(100 * ok / total, 1) if total else 100.0,
        "by_command": dict(kinds.most_common()),
        "ignored_commands": dict(ignored),
        "unknown_commands": {k: {"count": len(v), "examples": v[:5]} for k, v in unknown.items()},
    }


# ---------------------------------------------------------------- static: components, resources
def static_components(project: Project) -> dict:
    types: Counter = Counter()
    attrs_by_type: dict[int, Counter] = defaultdict(Counter)
    for p in project.pages:
        for c in [p.page] + p.comps:
            types[c.type] += 1
            for a in c.attrs:
                attrs_by_type[c.type][a] += 1
    rows, weight = [], 0.0
    used_n = unused_n = 0
    for t, cnt in attrs_by_type.items():
        if TYPE_SUPPORT.get(t, ("unsupported",))[0] == "unsupported":
            continue
        for a, n in cnt.items():
            if a in _STRUCT_ATTRS:
                continue
            if a in USED_ATTRS:
                used_n += n
            else:
                unused_n += n
    total = sum(types.values())
    for t, n in sorted(types.items(), key=lambda x: -x[1]):
        level, note = TYPE_SUPPORT.get(t, ("unsupported", "no rendering/behaviour"))
        weight += n * {"full": 1, "partial": 0.5}.get(level, 0)
        unused = sorted(a for a in attrs_by_type[t] if a not in USED_ATTRS and a not in _STRUCT_ATTRS)
        rows.append({"type": t, "name": TYPE_NAMES.get(t, f"type{t}"), "count": n, "support": level, "note": note,
                     "unused_attrs": unused})
    return {"total": total, "percent": round(100 * weight / total, 1) if total else 100.0, "types": rows,
            "attr_percent": round(100 * used_n / (used_n + unused_n), 1) if used_n + unused_n else 100.0,
            "attr_used": used_n, "attr_unused": unused_n}


def static_resources(project: Project) -> dict:
    """Resource facts. Used/unused counts come from the unused-resources analysis so both reports always agree
    (it also counts page backgrounds and references assigned in code, not only the components' own pic/font attributes)."""
    ua = unused.analyze(project)
    pic_refs: dict[int, list] = defaultdict(list)
    font_refs: dict[int, int] = Counter()
    for p in project.pages:
        for c in [p.page] + p.comps:
            for k in ("pic", "pic2"):
                v = c.attrs.get(k)
                if v is not None and v != 0xFFFF:
                    pic_refs[v].append(f"{p.name}.{c.name}")
            if "font" in c.attrs and c.type in (54, 59, 98, 116):
                font_refs[c.attrs["font"]] += 1
    miss_pic = {i: w[:5] for i, w in pic_refs.items() if i not in project.images}
    # check: does the size of the referenced image match the component (+-2 px)? -> shows how trustworthy the pic -> image mapping is
    chk = bad_dim = 0
    mism = []
    for p in project.pages:
        for c in p.comps:
            if c.type not in (98, 112) or "w" not in c.attrs:
                continue
            for k in ("pic", "pic2"):
                v = c.attrs.get(k, 0xFFFF)
                im = project.images.get(v)
                if v == 0xFFFF or im is None:
                    continue
                chk += 1
                if abs(im.width - c.attrs["w"]) > 2 or abs(im.height - c.attrs["h"]) > 2:
                    bad_dim += 1
                    mism.append(f"{p.name}.{c.name}.{k}: component {c.attrs['w']}x{c.attrs['h']}, image {im.width}x{im.height}")
    miss_font = {i: n for i, n in font_refs.items() if i not in project.fonts}
    return {
        "image_dim_checked": chk, "image_dim_mismatch": mism,
        "image_dim_percent": round(100 * (chk - bad_dim) / chk, 1) if chk else 100.0,
        "images_available": len(project.images),
        "images_used": sum(1 for x in ua["images"] if x["status"] == "used"),
        "images_unused": sum(1 for x in ua["images"] if x["status"] == "unused"),
        "images_uncertain": sum(1 for x in ua["images"] if x["status"] == "uncertain"),
        "unused_tft_bytes": ua["summary"]["images_unused_tft_bytes"],
        "fonts_used": sum(1 for x in ua["fonts"] if x["status"] == "used"),
        "images_missing": {str(k): v for k, v in miss_pic.items()},
        "fonts_available": len(project.fonts),
        "fonts_missing": {str(k): v for k, v in miss_font.items()},
        "fonts_note": "The .zi fonts cannot be rendered; the emulator uses a system font and takes the glyph height from the .zi header. "
                      "Font and image ids are positions in the main.HMI resource list.",
    }


def structure(project: Project) -> dict:
    bad = [p.name for p in project.pages if p.declared_objects != len(p.comps) + 1]
    dup = Counter(p.name for p in project.pages)
    return {
        "sections": project.sections,
        "pages": len(project.pages),
        "components": sum(len(p.comps) for p in project.pages),
        "pages_with_object_mismatch": bad,
        "duplicate_page_names": [n for n, c in dup.items() if c > 1],
        "percent": round(100 * (len(project.pages) - len(bad)) / len(project.pages), 1) if project.pages else 0.0,
        "warnings": project.warnings,
    }


# ---------------------------------------------------------------- scenario coverage
def _touched_refs(steps: list) -> set[str]:
    out: set[str] = set()
    for st in steps:
        out.update((st.get("set") or {}).keys() if isinstance(st.get("set"), dict) else [])
        if isinstance(st.get("ramp"), dict):
            out.add(st["ramp"].get("ref", ""))
        out.update(_touched_refs(st.get("steps", [])))
    return out


def scenario_coverage(project: Project, scenario_dir: Path | None, run: dict) -> dict:
    scns = scenario.load_dir(project, scenario_dir)
    discovered = [v for v in discover.build(project) if v["confidence"] in ("high", "medium")]
    keyb = ("keyb",)
    inputs = [v for v in discovered if not v["page"].startswith(keyb) and v["scope"] == "global" or v["confidence"] == "high" and not v["page"].startswith(keyb)]
    touched: set[str] = set()
    for s in scns:
        touched |= _touched_refs(s.steps)
    covered = [v["ref"] for v in inputs if v["ref"] in touched]
    runs = {r["id"]: r for r in run.get("scenario_runs", [])} if run.get("available") else {}
    rows = []
    for s in scns:
        r = runs.get(s.id)
        status = "ok"
        if s.issues:
            status = "issues"
        if r and (r["crash"] or r["scenarioErrors"] or r["errors"] or r["unknown"]):
            status = "error"
        rows.append({"id": s.id, "name": loc(s.name, "en"), "source": s.source, "issues": s.issues, "run": r, "status": status})
    good = sum(1 for r in rows if r["status"] == "ok")
    pages_hit = sorted({p for r in rows if r["run"] for p in r["run"]["visited"]})
    return {
        "count": len(scns), "percent": round(100 * good / len(scns), 1) if scns else 0.0,
        "scenarios": rows, "input_variables": len(inputs), "inputs_covered": len(covered),
        "inputs_uncovered": [v["ref"] for v in inputs if v["ref"] not in touched],
        "input_percent": round(100 * len(covered) / len(inputs), 1) if inputs else 100.0,
        "pages_visited": pages_hit, "pages_total": len(project.pages),
        "pages_percent": round(100 * len(pages_hit) / len(project.pages), 1) if project.pages else 0.0,
    }


# ---------------------------------------------------------------- assembly + HTML
def build(project: Project, scenario_dir: Path | None = None, run: dict | None = None) -> dict:
    """Coverage numbers. `run` is the result of the headless runtime smoke test (see emulator.smoke), if it was run."""
    st = structure(project)
    comps = static_components(project)
    code = static_code(project)
    res = static_resources(project)
    run = run or {"available": False, "reason": "the runtime smoke test was not run"}
    scn = scenario_coverage(project, scenario_dir, run)
    parts = [st["percent"], comps["percent"], comps["attr_percent"], code["percent"]] + ([run["percent"]] if run.get("available") else [])
    if scn["count"]:
        parts.append(scn["percent"])
    return {"project": project.name, "overall_percent": round(sum(parts) / len(parts), 1),
            "structure": st, "components": comps, "code": code, "resources": res, "runtime": run, "scenarios": scn, "sources": SOURCES}
