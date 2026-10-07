"""HTML / JSON output of the coverage analysis."""
from __future__ import annotations

import html as _html
import json
import shutil
from pathlib import Path

from ..analysis.coverage import build
from ..emulator import smoke
from ..parser import Project


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

    h.append("<h2>4. Resources (images and fonts)</h2>")
    h.append("<p class='note'>A Nextion project embeds pictures and fonts. For the emulator to look right it must find every "
             "picture and font that the display uses. This section answers three questions.</p>")
    h.append("<h3>4.1 Are all used pictures and fonts present?</h3><table><tr><th></th><th>In the file</th><th>Used</th>"
             "<th>Used but missing</th></tr>")
    h.append(f"<tr><td>Images</td><td>{rs['images_available']}</td><td>{rs['images_used']}</td>"
             f"<td>{len(rs['images_missing'])}</td></tr>")
    h.append(f"<tr><td>Fonts</td><td>{rs['fonts_available']}</td><td>{rs['fonts_used']}</td>"
             f"<td>{len(rs['fonts_missing'])}</td></tr></table>")
    h.append("<p>" + ("Nothing is missing: every referenced picture and font exists in the file."
                      if not rs["images_missing"] and not rs["fonts_missing"]
                      else "Missing: <code>" + _e(f"images {rs['images_missing']}, fonts {rs['fonts_missing']}") + "</code>") + "</p>")
    h.append(f"<p class='note'>\"Used\" is counted exactly as in the Unused resources report: component pictures, page backgrounds and "
             f"pictures assigned in code. The other {rs['images_unused']} image(s) "
             f"({rs['images_uncertain']} uncertain) are never shown – they only take space ({rs['unused_tft_bytes']:,} bytes in the display file) – "
             "see that report for the list.</p>")
    h.append("<h3>4.2 Is the picture-id mapping trustworthy?</h3>")
    h.append("<p class='note'>The file stores only a number for each picture. We map it to the right image by its position in the resource list. "
             "As a cross-check, a picture component should have about the size of its image.</p>")
    h.append(f"<p><b>{rs['image_dim_percent']}%</b> of {rs['image_dim_checked']} checked references match in size (±2 px)."
             + (" A few differences are normal: the designer may stretch or crop an image. " +
                "Different here: <code>" + _e("; ".join(rs["image_dim_mismatch"][:10])) + "</code>" if rs["image_dim_mismatch"] else "") + "</p>")
    h.append("<h3>4.3 Fonts</h3>")
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
    sdir = Path(scenario_dir) if scenario_dir else None
    run = smoke.runtime(project, out / ".smoke", sdir)
    cov = build(project, sdir, run)
    shutil.rmtree(out / ".smoke", ignore_errors=True)
    j, h = out / "coverage.json", out / "coverage.html"
    j.write_text(json.dumps(cov, ensure_ascii=False, indent=1), encoding="utf-8")
    h.write_text(render_html(cov), encoding="utf-8")
    return j, h, cov
