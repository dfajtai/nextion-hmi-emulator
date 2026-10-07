"""The launcher page (index.html in the output folder) that links every generated part."""
from __future__ import annotations

from pathlib import Path


LAUNCHER_LINKS = [
    ("Emulator (expert)", "emulator/index.html", "full emulator: macro recorder, variables, CSV, reports"),
    ("Emulator (basic, portable)", "portable/index.html", "simple mode only, scenarios found in its scenarios/ folder"),
    ("Coverage report", "coverage/coverage.html", ""),
    ("Unused resources", "unused/unused.html", ""),
    ("Navigation diagram", "summary/navigation.html", ""),
    ("Summary", "summary/summary.html", ""),
]


def write_launcher(root: str | Path, project_name: str, hmi_path: str | Path | None = None) -> Path:
    """Write <root>/index.html: one page linking every generated part (the files must exist)."""
    root = Path(root)
    rows = "".join(
        f'<li><a href="{href}">{title}</a>' + (f" <span>{note}</span>" if note else "") + "</li>"
        for title, href, note in LAUNCHER_LINKS if (root / href).is_file())
    stamp = ""
    if hmi_path and Path(hmi_path).is_file():
        import datetime
        import hashlib
        hp = Path(hmi_path)
        sha = hashlib.sha256(hp.read_bytes()).hexdigest()[:12]
        mt = datetime.datetime.fromtimestamp(hp.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        stamp = (f'<p class="stamp">Generated {now} from <code>{hp.name}</code> '
                 f'(modified {mt}, {hp.stat().st_size:,} bytes, sha256 {sha}…)</p>')
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{project_name}</title><style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;color:#111827;background:#f9fafb}}
@media(prefers-color-scheme:dark){{body{{color:#e5e7eb;background:#111827}}a{{color:#93c5fd}}code{{background:#1f2937}}}}
h1{{font-size:22px}}li{{margin:8px 0}}li span,p{{color:#6b7280;font-size:14px}}code{{background:#e5e7eb;padding:1px 5px;border-radius:4px}}
</style></head><body><h1>{project_name}</h1><ul>{rows}</ul>{stamp}
<p><b>Scenarios live in <code>portable/scenarios/</code>.</b> Without a server: put scenario <code>.json</code> files there (or drag a folder, e.g.
Downloads, onto <code>scripts/update_scenarios.bat</code>), run <code>scripts/update_scenarios.bat</code> / <code>.sh</code> (Python 3) and reload –
both emulators find them. The <code>portable/</code> folder can be copied anywhere: <code>start.bat</code> / <code>start.sh</code> in it does the same and opens the page.<br>
<b>With the helper server</b>: <code>./scripts/run.sh serve output/{project_name}</code> – recordings made in the expert
emulator are saved into <code>portable/scenarios/</code> and appear in the basic emulator automatically.</p></body></html>"""
    out = root / "index.html"
    out.write_text(html, encoding="utf-8")
    return out
