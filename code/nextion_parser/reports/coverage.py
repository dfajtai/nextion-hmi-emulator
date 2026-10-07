"""HTML / JSON output of the coverage analysis."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..analysis.coverage import build
from ..emulator import smoke
from ..parser import Project
from .doc import Bullets, Card, Cards, Details, Doc, Heading, Para, Table, code, esc, render, tag


def _pc(x) -> str:
    return f"{x}%"


def build_doc(cov: dict) -> Doc:
    """The coverage report as a document model (no HTML here)."""
    st, cp, cd, rs, rt, sc = cov["structure"], cov["components"], cov["code"], cov["resources"], cov["runtime"], cov["scenarios"]
    b: list = [Para("How much of the .HMI file the emulator reproduces. The values are computed from the analysis of the file; "
                    "they do not measure accuracy against a real display.", note=True)]
    cards = [Card("Overall", _pc(cov["overall_percent"]), "average of the layers below", cov["overall_percent"]),
             Card("Structure", _pc(st["percent"]), f"{st['pages']} pages, {st['components']} components", st["percent"]),
             Card("Component support", _pc(cp["percent"]), "full = 1, partial = 0.5", cp["percent"]),
             Card("Attributes", _pc(cp["attr_percent"]),
                  f"used {cp['attr_used']}, ignored {cp['attr_unused']} (style, border, transparent colour…)", cp["attr_percent"])]
    if sc["count"]:
        cards.append(Card("Scenarios", _pc(sc["percent"]), f"{sc['count']} total, run without errors", sc["percent"]))
    cards.append(Card("Code commands", _pc(cd["percent"]), f"{cd['total']} statements, unknown: {cd['unknown']}", cd["percent"]))
    if rt.get("available"):
        cards.append(Card("Runtime smoke test", _pc(rt["percent"]), f"{rt['events']} events executed", rt["percent"]))
        cards.append(Card("Reachable pages", _pc(rt["reachable_percent"]),
                          f"{len(rt['reachable'])}/{st['pages']} pages by clicking", rt["reachable_percent"]))
    b.append(Cards(cards))

    b.append(Heading("1. Structure"))
    s = st["sections"]
    b.append(Para(f"Directory: {s['total']} records, {s['live']} live, {s['deleted']} deleted (old copies). Other sections: {esc(s['other'])}."))
    if st["pages_with_object_mismatch"]:
        b.append(Para(f"Object count mismatch: {esc(', '.join(st['pages_with_object_mismatch']))}", note=True))
    if st["warnings"]:
        b.append(Details("Warnings", [Bullets([esc(w) for w in st["warnings"]])], open=True))
    else:
        b.append(Para("No warnings: the object count of every page matches its header.", note=True))

    b.append(Heading("2. Component types"))
    b.append(Table(["Type", "Count", "Support", "Note", "Unused attributes"], [
        [f"{esc(r['name'])} <span class='note'>({r['type']})</span>", str(r["count"]), tag(r["support"]), esc(r["note"]),
         code(", ".join(r["unused_attrs"]) or "–")] for r in cp["types"]]))

    b.append(Heading("3. Code commands (static)"))
    b.append(Para(f"{cd['total']} statements: supported {cd['supported']}, accepted but without effect {cd['ignored']}, unknown {cd['unknown']}."))
    b.append(Table(["Command", "Count"], [[code(k), str(v)] for k, v in cd["by_command"].items()]))
    if cd["ignored_commands"]:
        b.append(Para(f"Commands without effect (skipped by the emulator): {code(cd['ignored_commands'])}", note=True))
    if cd["unknown_commands"]:
        rows = [[code(k), str(v["count"]), "<br>".join(f"{code(e['where'])}: {code(e['line'])}" for e in v["examples"])]
                for k, v in cd["unknown_commands"].items()]
        b.append(Details("Unknown statements", [Table(["Command", "Count", "Examples"], rows)], open=True))

    b.append(Heading("4. Resources (images and fonts)"))
    b.append(Para("A Nextion project embeds pictures and fonts. For the emulator to look right it must find every "
                  "picture and font that the display uses. This section answers three questions.", note=True))
    b.append(Heading("4.1 Are all used pictures and fonts present?", 3))
    b.append(Table(["", "In the file", "Used", "Used but missing"], [
        ["Images", str(rs["images_available"]), str(rs["images_used"]), str(len(rs["images_missing"]))],
        ["Fonts", str(rs["fonts_available"]), str(rs["fonts_used"]), str(len(rs["fonts_missing"]))]]))
    b.append(Para("Nothing is missing: every referenced picture and font exists in the file."
                  if not rs["images_missing"] and not rs["fonts_missing"]
                  else "Missing: " + code(f"images {rs['images_missing']}, fonts {rs['fonts_missing']}")))
    b.append(Para("\"Used\" is counted exactly as in the Unused resources report: component pictures, page backgrounds and "
                  f"pictures assigned in code. The other {rs['images_unused']} image(s) "
                  f"({rs['images_uncertain']} uncertain) are never shown – they only take space ({rs['unused_tft_bytes']:,} bytes in the display file) – "
                  "see that report for the list.", note=True))
    b.append(Heading("4.2 Is the picture-id mapping trustworthy?", 3))
    b.append(Para("The file stores only a number for each picture. We map it to the right image by its position in the resource list. "
                  "As a cross-check, a picture component should have about the size of its image.", note=True))
    mism = (" A few differences are normal: the designer may stretch or crop an image. Different here: "
            + code("; ".join(rs["image_dim_mismatch"][:10]))) if rs["image_dim_mismatch"] else ""
    b.append(Para(f"<b>{rs['image_dim_percent']}%</b> of {rs['image_dim_checked']} checked references match in size (±2 px).{mism}"))
    b.append(Heading("4.3 Fonts", 3))
    b.append(Para(esc(rs["fonts_note"]), note=True))

    b.append(Heading("5. Runtime smoke test (Node)"))
    if not rt.get("available"):
        b.append(Para(f"Skipped: {esc(rt.get('reason'))}", note=True))
    else:
        b.append(Para(" ".join(tag(k, f"{k}: {v}") for k, v in rt["by_status"].items())))
        if rt["unreachable"]:
            b.append(Para(f"Pages not reachable by clicking from the start page: {code(', '.join(rt['unreachable']))} "
                          "<span class='note'>(keyboard pages usually open from the calling page through a variable)</span>"))
        if rt["problems"]:
            rows = [[code(f"{x['page']}.{x['comp']}.{x['event']}"), tag(x["status"]), esc(x["detail"])[:300]] for x in rt["problems"][:300]]
            b.append(Details("Problematic events", [Table(["Where", "Status", "Detail"], rows)], open=True))
        else:
            b.append(Para("Every event ran without errors."))

    b.append(Heading("6. Scenarios (MCU simulation)"))
    if not sc["count"]:
        b.append(Para("No scenarios (the --scenarios folder is empty or missing).", note=True))
    else:
        b.append(Para(f"{sc['count']} scenarios; they touch {sc['input_percent']}% of the input variables ({sc['inputs_covered']}/{sc['input_variables']}); "
                      f"the runs visited {len(sc['pages_visited'])}/{sc['pages_total']} pages ({sc['pages_percent']}%)."))
        rows = []
        for r in sc["scenarios"]:
            run = r["run"]
            notes = list(r["issues"])
            if run:
                notes += ([run["crash"]] if run["crash"] else []) + run["scenarioErrors"] + run["errors"] + [f"unknown statement: {u}" for u in run["unknown"]]
                if run["refErrors"]:
                    notes.append("unresolved reads: " + ", ".join(run["refErrors"][:4]))
            rows.append([f"{esc(r['name'])}<br><span class='note'>{esc(r['source'])}</span>", tag("ok" if r["status"] == "ok" else "error", r["status"]),
                         str(run["steps"]) if run else "–", f"{(run['simulatedMs'] / 1000) if run else 0:.1f} s", esc("; ".join(notes)) or "–"])
        b.append(Table(["Scenario", "Status", "Steps", "Sim. time", "Notes"], rows))
        if sc["inputs_uncovered"]:
            b.append(Details("Inputs not touched by any scenario", [Para(code(", ".join(sc["inputs_uncovered"])))]))
    b.append(Heading("Sources"))
    b.append(Bullets([f"<a href='{esc(u)}'>{esc(t)}</a>" for t, u in cov["sources"]]))
    return Doc(f"{cov['project']} – simulator coverage", b)


def write(project: Project, out_dir: str | Path, scenario_dir: str | Path | None = None) -> tuple[Path, Path, dict]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sdir = Path(scenario_dir) if scenario_dir else None
    run = smoke.runtime(project, out / ".smoke", sdir)
    cov = build(project, sdir, run)
    shutil.rmtree(out / ".smoke", ignore_errors=True)
    j, h = out / "coverage.json", out / "coverage.html"
    j.write_text(json.dumps(cov, ensure_ascii=False, indent=1), encoding="utf-8")
    h.write_text(render(build_doc(cov)), encoding="utf-8")
    return j, h, cov
