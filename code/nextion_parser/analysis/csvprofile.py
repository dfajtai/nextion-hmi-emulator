"""A *guessed* starting point for ``csv_profiles.json`` (the targets of the CSV statistics import).

The profile says into which variables the mean / SD / CV / count go, how to reach that page with button presses and which
waveform shows the raw data. Nothing in the .HMI states this, so it is inferred from component names and the page navigation;
the result is a skeleton to be checked and corrected by a human.
"""
from __future__ import annotations

from collections import deque

from ..parser import Project
from .navigation import navigation

NUMERIC = {54, 59, 52}                       # number, xfloat, variable
TEXT, BUTTON, WAVEFORM = 116, 98, 0
KEYS = {                                     # profile key -> substrings of a component name (lower case)
    "quantity": ("quantity", "count", "cnt", "egyed"),
    "mean": ("mean", "avg", "average", "atlag"),
    "sd": ("sd", "std", "dev", "szoras"),
    "cv": ("cv", "variation"),
}
GROUP_HINTS = ("group", "name", "csoport", "grp")


def _clicks(project: Project) -> dict[str, list[tuple[str, str]]]:
    """page -> [(target page, button name)] for jumps triggered by a button press."""
    adj: dict[str, list[tuple[str, str]]] = {}
    for (a, b), labels in navigation(project)[0].items():
        for lab in sorted(labels):
            comp, _, ev = lab.rpartition(".")
            if comp and not comp.startswith("auto@") and ev in ("down", "up"):
                adj.setdefault(a, []).append((b, comp))
    return adj


def _path(adj: dict, start: str, goal: str) -> list[str] | None:
    """Shortest list of button names that leads from `start` to `goal` (BFS)."""
    seen, q = {start}, deque([(start, [])])
    while q:
        page, path = q.popleft()
        if page == goal:
            return path
        for nxt, btn in adj.get(page, []):
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, path + [btn]))
    return None


def guess_profile(project: Project, start: str | None = None) -> dict | None:
    """The best guess for the ``stats`` profile, or None when no page looks like a statistics page (needs >= 2 matches)."""
    best, best_found = None, {}
    for pg in project.pages:
        found = {}
        for c in pg.comps:
            if c.type in NUMERIC:
                for key, hints in KEYS.items():
                    if key not in found and any(h in c.name.lower() for h in hints):
                        found[key] = f"{pg.name}.{c.name}.val"
        if len(found) > len(best_found):
            best, best_found = pg, found
    if best is None or len(best_found) < 2:
        return None
    prof: dict = {"page": best.name}
    adj = _clicks(project)
    path = _path(adj, start or project.start_page or project.pages[0].name, best.name)
    if path:
        prof["path"] = path
    prof.update(best_found)
    grp = next((c for c in best.comps if c.type == TEXT and any(h in c.name.lower() for h in GROUP_HINTS)), None)
    if grp:
        prof["group"] = f"{best.name}.{grp.name}.txt"
    wave = next(((p.name, c.name) for p in project.pages for c in p.comps if c.type == WAVEFORM), None)
    if wave:
        w = {"ref": f"{wave[0]}.{wave[1]}", "points": 400}
        btn = next((b for tgt, b in adj.get(best.name, []) if tgt == wave[0]), None)
        if btn:
            w["click"] = btn                 # the button on the statistics page that opens the waveform page
        prof["wave"] = w
    return {"_note": "GUESSED from component names and navigation - check every entry before use", "stats": prof}
