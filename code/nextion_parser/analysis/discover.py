"""Discover simulation input variables by static analysis.

From the display code we find which values the code *reads* but never *writes*: these are most likely fed by the
MCU over the serial line (e.g. ``pageA.level.val=80``).

Output: ``variables.discovered.json`` (always regenerated) + an optional hand-edited ``variables.json``
(label, range, unit, group, presets, ``hidden``) that is overlaid on the discovered data.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from ..parser import Project
from ..parser.codeutil import statements as _statements

_REF = re.compile(r"(?<![\w.\"])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*){1,2})(?![\w(])")
_PB = re.compile(r"p\[[^\]]*\]\.b\[[^\]]*\]\.\w+")
_STR = re.compile(r'"(?:[^"\\]|\\.)*"')
_CMP = re.compile(r"(?P<ref>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*){1,2})\s*(?P<op>==|!=|<=|>=|<|>)\s*(?P<n>-?\d+)")
_CMP_REV = re.compile(r"(?P<n>-?\d+)\s*(?P<op>==|!=|<=|>=|<|>)\s*(?P<ref>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*){1,2})")
_FLIP = {"<": ">", ">": "<", "<=": ">=", ">=": "<=", "==": "==", "!=": "!="}
_KEYWORDS = {"if", "else", "for", "while", "int"}
MCU_TYPES = {52, 54, 59, 1, 106, 116, 56, 57}


def _split_args(s: str) -> list[str]:
    out, d, q, cur = [], 0, False, ""
    for ch in s:
        if ch == '"':
            q = not q
        if not q:
            if ch in "([":
                d += 1
            elif ch in ")]":
                d -= 1
            elif ch == "," and d == 0:
                out.append(cur.strip())
                cur = ""
                continue
        cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


class _Resolver:
    def __init__(self, project: Project):
        self.pages = {p.name: {c.name: c for c in p.comps} for p in project.pages}
        self.globals = set()

    def ref(self, text: str, page: str) -> str | None:
        parts = text.split(".")
        if len(parts) == 3 and parts[0] in self.pages and parts[1] in self.pages[parts[0]]:
            return text
        if len(parts) == 2 and parts[0] in self.pages[page]:
            return f"{page}.{parts[0]}.{parts[1]}"
        return None


def _refs(expr: str) -> list[str]:
    expr = _PB.sub(" ", _STR.sub('""', expr))
    return [m.group(1) for m in _REF.finditer(expr) if m.group(1).split(".")[0] not in _KEYWORDS]


def _usage(project: Project) -> dict:
    res = _Resolver(project)
    reads: dict[str, set] = defaultdict(set)
    writes: dict[str, set] = defaultdict(set)
    thresholds: dict[str, set] = defaultdict(set)

    def read(expr, page, where):
        for r in _refs(expr):
            q = res.ref(r, page)
            if q:
                reads[q].add(where)

    def write(target, page, where):
        q = res.ref(target.strip(), page)
        if q:
            writes[q].add(where)

    def thresh(cond, page):
        c = _STR.sub('""', cond)
        for m in _CMP.finditer(c):
            q = res.ref(m.group("ref"), page)
            if q:
                thresholds[q].add((m.group("op"), int(m.group("n"))))
        for m in _CMP_REV.finditer(c):
            q = res.ref(m.group("ref"), page)
            if q:
                thresholds[q].add((_FLIP[m.group("op")], int(m.group("n"))))

    for p in project.pages:
        for cname, code in [("(page)", p.code)] + [(c.name, c.code) for c in p.comps]:
            for ev, lines in code.items():
                where = f"{p.name}.{cname}.{ev}"
                for s in _statements(lines):
                    m = re.match(r"^(if|while)\s*\((.*)\)\s*(.*)$", s)
                    if m:
                        read(m.group(2), p.name, where)
                        thresh(m.group(2), p.name)
                        s = m.group(3).strip()
                        if not s:
                            continue
                    m = re.match(r"^for\s*\((.*?);(.*?);(.*)\)$", s)
                    if m:
                        for part in m.groups():
                            read(part, p.name, where)
                        thresh(m.group(2), p.name)
                        continue
                    s = re.sub(r"^else\s*", "", s)
                    m = re.match(r"^(covx|cov)\s+(.*)$", s)
                    if m:
                        a = _split_args(m.group(2))
                        read(a[0], p.name, where)
                        if len(a) > 1:
                            write(a[1], p.name, where)
                        continue
                    m = re.match(r"^(substr|btlen|strlen)\s+(.*)$", s)
                    if m:
                        a = _split_args(m.group(2))
                        read(a[0], p.name, where)
                        if len(a) > 1:
                            write(a[1], p.name, where)
                        for extra in a[2:]:
                            read(extra, p.name, where)
                        continue
                    m = re.match(r"^repo\s+(.*)$", s)
                    if m:
                        write(_split_args(m.group(1))[0], p.name, where)
                        continue
                    m = re.match(r"^(wepo|prints|print|printh|vis|click)\s+(.*)$", s)
                    if m:
                        if m.group(1) not in ("vis", "click", "printh"):
                            read(m.group(2), p.name, where)
                        continue
                    m = re.match(r"^(.+?)(\+\+|--)$", s)
                    if m:
                        write(m.group(1), p.name, where)
                        read(m.group(1), p.name, where)
                        continue
                    m = re.match(r"^([A-Za-z_][\w\.]*?)\s*(\+=|-=|\*=|\/=|=)\s*(.+)$", s)
                    if m:
                        write(m.group(1), p.name, where)
                        if m.group(2) != "=":
                            read(m.group(1), p.name, where)
                        read(m.group(3), p.name, where)
    return {"reads": reads, "writes": writes, "thresholds": thresholds}


def _test_values(th: set) -> list[int]:
    vals: set[int] = set()
    for op, n in th:
        vals.update({">": (n, n + 1), ">=": (n - 1, n), "<": (n - 1, n), "<=": (n, n + 1), "==": (n, n + 1), "!=": (n, n + 1)}[op])
    return sorted(vals)


def build(project: Project) -> list[dict]:
    u = _usage(project)
    out = []
    for p in project.pages:
        for c in p.comps:
            if c.type not in MCU_TYPES:
                continue
            attrs = ["val"] if c.type != 116 else ["txt"]
            if c.type == 52:
                attrs = ["val", "txt"]
            for a in attrs:
                ref = f"{p.name}.{c.name}.{a}"
                r, w = sorted(u["reads"].get(ref, [])), sorted(u["writes"].get(ref, []))
                if a == "txt" and c.type == 52 and not r and not w:
                    continue
                if w:
                    continue                          # written by the display code -> not an external input
                th = u["thresholds"].get(ref, set())
                if r:
                    conf = "high"                     # read by the code but never written
                elif c.type in (54, 59, 1, 106, 52):
                    conf = "medium"                   # data display / variable that the code does not use
                elif c.type == 116 and not (c.attrs.get("txt") or "").strip():
                    conf = "low"                      # empty text field: probably filled at run time
                else:
                    continue
                entry = {
                    "ref": ref, "page": p.name, "obj": c.name, "attr": a, "type": c.type_name,
                    "scope": "global" if c.attrs.get("vscope") == 1 else "local",
                    "initial": c.attrs.get(a), "confidence": conf,
                    "read_in": r[:6], "thresholds": [f"{op}{n}" for op, n in sorted(th, key=lambda t: t[1])],
                    "test_values": _test_values(th),
                }
                if c.type in (1, 106):
                    entry["min"], entry["max"] = c.attrs.get("minval", 0), c.attrs.get("maxval", 100)
                if c.type == 59:
                    entry["decimals"] = c.attrs.get("vvs1", 0)
                out.append(entry)
    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda e: (order[e["confidence"]], e["scope"] != "global", e["page"], e["obj"]))
    return out


def variables_template(discovered: list[dict]) -> dict:
    """An editable ``variables.json`` skeleton from the discovered list: every input variable with a placeholder label
    (the object name), its page as the group, the initial value and the probe values found in the code as presets.
    Fill in real labels / units / min / max / descriptions (hu and en) and save it as ``scenarios/variables.json``."""
    out: dict = {}
    for v in discovered:
        item: dict = {"label": {"hu": v["obj"], "en": v["obj"]}, "group": {"hu": v["page"], "en": v["page"]}}
        if v.get("min") is not None and v.get("max") is not None:
            item["min"], item["max"] = v["min"], v["max"]
        if v["attr"] == "txt" and v.get("initial"):
            item["initial"] = v["initial"]
        if v.get("test_values"):
            item["presets"] = {str(x): x for x in v["test_values"]}
        out[v["ref"]] = item
    return out


def merge(discovered: list[dict], overrides: dict | None) -> list[dict]:
    """Overlay the hand-edited variables.json on the discovered list; new (undiscovered) references may be added too."""
    ov = dict(overrides or {})
    out = []
    seen = set()
    for e in discovered:
        o = ov.get(e["ref"], {})
        if o.get("hidden"):
            seen.add(e["ref"])
            continue
        out.append({**e, **{k: v for k, v in o.items() if k != "hidden"}, "curated": e["ref"] in ov})
        seen.add(e["ref"])
    for ref, o in ov.items():
        if ref not in seen and not o.get("hidden"):
            out.append({"ref": ref, "confidence": "manual", "curated": True, **o})
    return out


def load_overrides(scenario_dir: Path | None) -> dict:
    if scenario_dir and (scenario_dir / "variables.json").is_file():
        return json.loads((scenario_dir / "variables.json").read_text(encoding="utf-8"))
    return {}
