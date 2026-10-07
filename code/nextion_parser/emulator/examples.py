"""Picks names from the actual project for examples and placeholders (help text, input hints), so that nothing in the
generic front-end or documentation refers to one particular project."""
from __future__ import annotations

from ..parser import Project

NUMERIC_TYPES = {54, 59, 52}          # number, xfloat, variable
BUTTON, WAVEFORM = 98, 0


def pick_examples(project: Project, data: dict) -> dict:
    """{'page', 'other_page', 'ref', 'btn', 'wave'}: real names from the project; generic fallbacks when it has none."""
    start = data.get("start") or (project.pages[0].name if project.pages else "page")
    names = [p.name for p in project.pages]
    other = next((n for n in names if n != start), start)
    ref = next((v["ref"] for v in data.get("variables", []) if v["ref"].endswith(".val")), None)
    if ref is None:
        ref = next((f"{p.name}.{c.name}.val" for p in project.pages for c in p.comps if c.type in NUMERIC_TYPES), None)
    first_page = project.page(start) or (project.pages[0] if project.pages else None)
    btn = next((c.name for c in (first_page.comps if first_page else []) if c.type == BUTTON), None) \
        or next((c.name for p in project.pages for c in p.comps if c.type == BUTTON), None)
    wave = next((f"{p.name}.{c.name}" for p in project.pages for c in p.comps if c.type == WAVEFORM), None)
    return {"page": start, "other_page": other, "ref": ref or f"{start}.component.val", "btn": btn or "button", "wave": wave}
