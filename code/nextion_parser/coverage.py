"""Simulator coverage report produced after the conversion: coverage.json + coverage.html.

Three layers:
  1. structure  - what could be read from the file (pages, object counts, images, fonts)
  2. static     - does the emulator support the component types, attributes and commands
  3. runtime (Node) - does the emulator core really run every event of every page
The static support tables mirror the behaviour of ``templates/nextion_core.js`` / ``emulator.html``;
the tests make sure they do not drift apart.
"""
from __future__ import annotations

import html as _html
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from importlib import resources
from pathlib import Path

from . import discover, emulator, scenario
from .codeutil import statements as _statements
from .hmi import TYPE_NAMES, Project
from .i18n import loc

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
        "images_available": len(project.images), "images_referenced": len(pic_refs),
        "images_missing": {str(k): v for k, v in miss_pic.items()},
        "fonts_available": len(project.fonts), "fonts_referenced": len(font_refs),
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


# ---------------------------------------------------------------- runtime (Node)
def runtime(project: Project, workdir: Path | None = None, scenario_dir: Path | None = None) -> dict:
    node = shutil.which("node")
    if not node:
        return {"available": False, "reason": "`node` was not found on the PATH; the runtime smoke test is skipped"}
    tmp = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="nxcov_"))
    tmp.mkdir(parents=True, exist_ok=True)
    data = emulator.build_data(project, scenario_dir=scenario_dir)
    (tmp / "data.js").write_text("const DATA=" + json.dumps(data, ensure_ascii=False) + ";", encoding="utf-8")
    tpl = resources.files("nextion_parser").joinpath("templates")
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
def build(project: Project, workdir: Path | None = None, scenario_dir: Path | None = None) -> dict:
    st = structure(project)
    comps = static_components(project)
    code = static_code(project)
    res = static_resources(project)
    run = runtime(project, workdir, scenario_dir)
    scn = scenario_coverage(project, scenario_dir, run)
    parts = [st["percent"], comps["percent"], comps["attr_percent"], code["percent"]] + ([run["percent"]] if run.get("available") else [])
    if scn["count"]:
        parts.append(scn["percent"])
    return {"project": project.name, "overall_percent": round(sum(parts) / len(parts), 1),
            "structure": st, "components": comps, "code": code, "resources": res, "runtime": run, "scenarios": scn, "sources": SOURCES}


def _e(x) -> str:
    return _html.escape(str(x))


def _bar(p: float) -> str:
    cls = "ok" if p >= 90 else "warn" if p >= 60 else "bad"
    return f'<div class="bar"><i class="{cls}" style="width:{p}%"></i></div>'


def _card(title: str, pct, sub: str) -> str:
    return (f'<div class="card"><div class="k">{_e(title)}</div><div class="v">{pct}%</div>{_bar(pct)}'
            f'<div class="s">{_e(sub)}</div></div>')


def render_html(cov: dict) -> str:
    st, cp, cd, rs, rt = cov["structure"], cov["components"], cov["code"], cov["resources"], cov["runtime"]
    h = [f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>{_e(cov['project'])} – coverage</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
:root{{--bg:#f4f5f7;--fg:#1c1f24;--card:#fff;--line:#d5d9e0;--mut:#667085;--ok:#15803d;--warn:#b45309;--bad:#b91c1c}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14161a;--fg:#e6e8ec;--card:#1d2026;--line:#333842;--mut:#98a2b3;--ok:#4ade80;--warn:#fbbf24;--bad:#f87171}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif;max-width:1100px;margin:auto}}
h1{{font-size:20px}}h2{{font-size:16px;margin-top:28px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}}
.k{{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}}.v{{font-size:28px;font-weight:600}}.s{{color:var(--mut);font-size:12px}}
.bar{{height:6px;background:var(--line);border-radius:3px;margin:6px 0}}.bar i{{display:block;height:100%;border-radius:3px}}
i.ok{{background:var(--ok)}}i.warn{{background:var(--warn)}}i.bad{{background:var(--bad)}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}}
th,td{{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-size:12px;color:var(--mut)}}
.tag{{padding:1px 8px;border-radius:10px;font-size:12px;color:#fff}}.full,.supported,.ok{{background:var(--ok)}}.partial,.ignored,.redirect{{background:var(--warn)}}
.unsupported,.unknown,.error,.crash,.bad{{background:var(--bad)}}.unresolved-ref{{background:var(--warn)}}
code{{font:12px ui-monospace,monospace}}details{{margin:6px 0}}summary{{cursor:pointer}}
.note{{color:var(--mut)}}
</style><body><h1>{_e(cov['project'])} – simulator coverage</h1>
<p class="note">How much of the .HMI file the emulator reproduces. The values are computed from the analysis of the file; they do not measure accuracy against a real display.</p>
<div class="grid">"""]
    h.append(_card("Overall", cov["overall_percent"], "average of the layers below"))
    h.append(_card("Structure", st["percent"], f"{st['pages']} pages, {st['components']} components"))
    h.append(_card("Component support", cp["percent"], "full = 1, partial = 0.5"))
    h.append(_card("Attributes", cp["attr_percent"], f"used {cp['attr_used']}, ignored {cp['attr_unused']} (style, border, transparent colour…)"))
    if cov["scenarios"]["count"]:
        h.append(_card("Scenarios", cov["scenarios"]["percent"], f"{cov['scenarios']['count']} total, run without errors"))
    h.append(_card("Code commands", cd["percent"], f"{cd['total']} statements, unknown: {cd['unknown']}"))
    if rt.get("available"):
        h.append(_card("Runtime smoke test", rt["percent"], f"{rt['events']} events executed"))
        h.append(_card("Reachable pages", rt["reachable_percent"], f"{len(rt['reachable'])}/{st['pages']} pages by clicking"))
    h.append("</div>")

    h.append("<h2>1. Structure</h2>")
    s = st["sections"]
    h.append(f"<p>Directory: {s['total']} records, {s['live']} live, {s['deleted']} deleted (old copies). "
             f"Other sections: {_e(s['other'])}.</p>")
    if st["pages_with_object_mismatch"]:
        h.append(f"<p class='note'>Object count mismatch: {_e(', '.join(st['pages_with_object_mismatch']))}</p>")
    if st["warnings"]:
        h.append("<details open><summary>Warnings</summary><ul>" + "".join(f"<li>{_e(w)}</li>" for w in st["warnings"]) + "</ul></details>")
    else:
        h.append("<p class='note'>No warnings: the object count of every page matches its header.</p>")

    h.append("<h2>2. Component types</h2><table><tr><th>Type</th><th>Count</th><th>Support</th><th>Note</th><th>Unused attributes</th></tr>")
    for r in cp["types"]:
        h.append(f"<tr><td>{_e(r['name'])} <span class='note'>({r['type']})</span></td><td>{r['count']}</td>"
                 f"<td><span class='tag {r['support']}'>{_e(r['support'])}</span></td><td>{_e(r['note'])}</td>"
                 f"<td><code>{_e(', '.join(r['unused_attrs']) or '–')}</code></td></tr>")
    h.append("</table>")

    h.append("<h2>3. Code commands (static)</h2>")
    h.append(f"<p>{cd['total']} statements: supported {cd['supported']}, accepted but without effect {cd['ignored']}, unknown {cd['unknown']}.</p>")
    h.append("<table><tr><th>Command</th><th>Count</th></tr>" + "".join(
        f"<tr><td><code>{_e(k)}</code></td><td>{v}</td></tr>" for k, v in cd["by_command"].items()) + "</table>")
    if cd["ignored_commands"]:
        h.append(f"<p class='note'>Commands without effect (skipped by the emulator): <code>{_e(cd['ignored_commands'])}</code></p>")
    if cd["unknown_commands"]:
        h.append("<details open><summary>Unknown statements</summary><table><tr><th>Command</th><th>Count</th><th>Examples</th></tr>")
        for k, v in cd["unknown_commands"].items():
            ex = "<br>".join(f"<code>{_e(e['where'])}</code>: <code>{_e(e['line'])}</code>" for e in v["examples"])
            h.append(f"<tr><td><code>{_e(k)}</code></td><td>{v['count']}</td><td>{ex}</td></tr>")
        h.append("</table></details>")

    h.append("<h2>4. Resources</h2>")
    h.append(f"<p>Images: {rs['images_available']} available, {rs['images_referenced']} referenced. "
             f"Fonts: {rs['fonts_available']} available, {rs['fonts_referenced']} referenced.</p>")
    for label, key in (("Missing images", "images_missing"), ("Missing fonts", "fonts_missing")):
        h.append(f"<p>{label}: <code>{_e(rs[key] or 'none')}</code></p>")
    h.append(f"<p>Size check of the image mapping: {rs['image_dim_percent']}% match ({rs['image_dim_checked']} references)."
             + ("" if not rs["image_dim_mismatch"] else " Mismatches: <code>" + _e("; ".join(rs["image_dim_mismatch"][:10])) + "</code>") + "</p>")
    h.append(f"<p class='note'>{_e(rs['fonts_note'])}</p>")

    h.append("<h2>5. Runtime smoke test (Node)</h2>")
    if not rt.get("available"):
        h.append(f"<p class='note'>Skipped: {_e(rt.get('reason'))}</p>")
    else:
        h.append("<p>" + " ".join(f"<span class='tag {k}'>{_e(k)}: {v}</span>" for k, v in rt["by_status"].items()) + "</p>")
        if rt["unreachable"]:
            h.append(f"<p>Pages not reachable by clicking from the start page: <code>{_e(', '.join(rt['unreachable']))}</code> "
                     "<span class='note'>(keyboard pages usually open from the calling page through a variable)</span></p>")
        if rt["problems"]:
            h.append("<details open><summary>Problematic events</summary><table><tr><th>Where</th><th>Status</th><th>Detail</th></tr>")
            for x in rt["problems"][:300]:
                h.append(f"<tr><td><code>{_e(x['page'])}.{_e(x['comp'])}.{_e(x['event'])}</code></td>"
                         f"<td><span class='tag {x['status']}'>{_e(x['status'])}</span></td><td>{_e(x['detail'])[:300]}</td></tr>")
            h.append("</table></details>")
        else:
            h.append("<p>Every event ran without errors.</p>")
    sc = cov["scenarios"]
    h.append("<h2>6. Scenarios (MCU simulation)</h2>")
    if not sc["count"]:
        h.append("<p class='note'>No scenarios (the --scenarios folder is empty or missing).</p>")
    else:
        h.append(f"<p>{sc['count']} scenarios; they touch {sc['input_percent']}% of the input variables ({sc['inputs_covered']}/{sc['input_variables']}); "
                 f"the runs visited {len(sc['pages_visited'])}/{sc['pages_total']} pages ({sc['pages_percent']}%).</p>")
        h.append("<table><tr><th>Scenario</th><th>Status</th><th>Steps</th><th>Sim. time</th><th>Notes</th></tr>")
        for r in sc["scenarios"]:
            run = r["run"]
            notes = list(r["issues"])
            if run:
                notes += ([run["crash"]] if run["crash"] else []) + run["scenarioErrors"] + run["errors"] + [f"unknown statement: {u}" for u in run["unknown"]]
                if run["refErrors"]:
                    notes.append("unresolved reads: " + ", ".join(run["refErrors"][:4]))
            h.append(f"<tr><td>{_e(r['name'])}<br><span class='note'>{_e(r['source'])}</span></td><td><span class='tag {'ok' if r['status']=='ok' else 'error'}'>{_e(r['status'])}</span></td>"
                     f"<td>{run['steps'] if run else '–'}</td><td>{(run['simulatedMs']/1000) if run else 0:.1f} s</td><td>{_e('; '.join(notes)) or '–'}</td></tr>")
        h.append("</table>")
        if sc["inputs_uncovered"]:
            h.append("<details><summary>Inputs not touched by any scenario</summary><p><code>" + _e(", ".join(sc["inputs_uncovered"])) + "</code></p></details>")
    h.append("<h2>Sources</h2><ul>" + "".join(f"<li><a href='{_e(u)}'>{_e(t)}</a></li>" for t, u in cov["sources"]) + "</ul></body></html>")
    return "".join(h)


def write(project: Project, out_dir: str | Path, scenario_dir: str | Path | None = None) -> tuple[Path, Path, dict]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cov = build(project, out / ".smoke", Path(scenario_dir) if scenario_dir else None)
    shutil.rmtree(out / ".smoke", ignore_errors=True)
    j, h = out / "coverage.json", out / "coverage.html"
    j.write_text(json.dumps(cov, ensure_ascii=False, indent=1), encoding="utf-8")
    h.write_text(render_html(cov), encoding="utf-8")
    return j, h, cov
