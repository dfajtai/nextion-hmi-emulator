from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import emulator, parser
from .analysis import discover, scenario, unused
from .emulator import serve
from .reports import coverage, summary
from .reports import discover as discover_report
from .reports import unused as unused_report


def _out(args, hmi_path: Path, sub: str) -> Path:
    return Path(args.output) if args.output else Path("output") / hmi_path.stem / sub


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nextion_parser",
                                 description="Analyze a Nextion .HMI file and generate a browser emulator and reports")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, helptext in (("summary", "summaries: pages.json, navigation.mmd/.html, summary.html"),
                           ("emulator", "generate the browser emulator (+ help.html)"),
                           ("coverage", "simulator coverage report (coverage.html/json)"),
                           ("unused", "report of unused images/fonts/pages (unused.html/csv/json)"),
                           ("discover", "discover simulation input variables (variables.discovered.json)"),
                           ("portable", "portable basic (simple-mode only) emulator folder with an empty scenarios/ folder"),
                           ("all", "summaries + unused report + discovery + coverage + emulator")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("hmi", help="path of the .HMI file")
        p.add_argument("-o", "--output", help="output folder (default: output/<file name>/...)")
        if name in ("emulator", "coverage", "all", "discover", "portable"):
            p.add_argument("--lenient", action="store_true",
                           help="exit with 0 even if some scenarios do not match the HMI (default: exit code 4, everything is still generated)")
            p.add_argument("--scenarios", metavar="DIR",
                           help="folder of scenarios (JSON) and variables.json (default: <hmi folder>/scenarios, if it exists)")
        if name in ("emulator", "all", "portable"):
            p.add_argument("--start", help="start page name (default: from the `page N` line of Program.s)")
            p.add_argument("--screen", metavar="WxH", help="emulator screen size in pixels, e.g. 800x480 (default: the project resolution)")
            p.add_argument("--zoom", metavar="Z|fit", help="initial zoom: a number or 'fit' (default: fit)")
            p.add_argument("--lang", choices=("hu", "en"), default="hu",
                           help="default GUI language of the emulator and help (the user can switch at run time; default: hu)")
    sp = sub.add_parser("serve", help="serve a generated folder; scenarios of the portable package load and save automatically")
    sp.add_argument("root", nargs="?", default=".", help="folder to serve, e.g. output/<name> (default: current)")
    sp.add_argument("--scenarios", metavar="DIR", help="scenarios folder (default: <root>/portable/scenarios, else <root>/scenarios)")
    sp.add_argument("--port", type=int, default=8765)
    sp.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = ap.parse_args(argv)
    if args.cmd == "serve":
        serve.run(Path(args.root), Path(args.scenarios) if args.scenarios else None, args.port, not args.no_open)
        return 0

    path = Path(args.hmi)
    if not path.is_file():
        print(f"Not found: {path}", file=sys.stderr)
        return 2
    project = parser.load(path)
    print(f"{project.name}: {len(project.pages)} pages, "
          f"{sum(len(p.comps) for p in project.pages)} components, {len(project.images)} images")

    sdir = Path(args.scenarios) if getattr(args, "scenarios", None) else (path.parent / "scenarios")
    sdir = sdir if sdir.is_dir() else None
    if sdir:
        print(f"  scenario folder: {sdir}")
    broken = []
    if sdir and args.cmd in ("emulator", "portable", "coverage", "all"):
        broken = [x for x in scenario.load_dir(project, sdir) if x.issues]
    sub = (lambda n: Path(args.output) / n) if args.output and args.cmd == "all" else (lambda n: _out(args, path, n))
    if args.cmd in ("summary", "all"):
        for f in summary.write_all(project, sub("summary")):
            print("  ", f)
    if args.cmd in ("unused", "all"):
        up = unused_report.write(project, sub("unused"))
        rep = unused.analyze(project)["summary"]
        print("  ", up["html"])
        print("  ", up["csv"])
        print(f"   unused: {rep['images_unused']}/{rep['images_total']} images, "
              f"{rep['fonts_unused']}/{rep['fonts_total']} fonts, {rep['pages_unreferenced']} unreferenced pages")
    if args.cmd in ("discover", "all"):
        files = discover_report.write(project, sub("discover"))
        for f in files:
            print("  ", f)
        print(f"   discover: {len(discover.build(project))} input variables; the *.template.json files are editable skeletons")
    if args.cmd in ("coverage", "all"):
        j, h, cov = coverage.write(project, sub("coverage"), sdir)
        print("  ", h)
        print("  ", j)
        rt = cov["runtime"]
        print(f"   coverage: overall {cov['overall_percent']}% | structure {cov['structure']['percent']}% | "
              f"components {cov['components']['percent']}% | attributes {cov['components']['attr_percent']}% | code {cov['code']['percent']}% | "
              + (f"runtime {rt['percent']}%" if rt.get("available") else "runtime: skipped")
              + (f" | scenarios {cov['scenarios']['percent']}%" if cov["scenarios"]["count"] else ""))
    # the emulator is generated last so that it can link to the other reports (menu)
    if args.cmd == "portable":
        try:
            screen = emulator.parse_size(args.screen) if args.screen else None
            out = Path(args.output) if args.output else Path("output") / path.stem / "portable"
            print("  ", emulator.generate(project, out, args.start, screen, args.zoom, sdir, args.lang, portable=True))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    if args.cmd == "all":
        out = sub("portable")
        emulator.generate(project, out, args.start, emulator.parse_size(args.screen) if args.screen else None,
                          args.zoom, sdir, args.lang, portable=True)
        print("  ", out / "index.html")
    if args.cmd in ("emulator", "all"):
        try:
            screen = emulator.parse_size(args.screen) if args.screen else None
            print("  ", emulator.generate(project, sub("emulator"), args.start, screen, args.zoom, sdir, args.lang))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    if args.cmd == "all":
        root = Path(args.output) if args.output else Path("output") / path.stem
        print("  ", emulator.write_scripts(root))
        print("  ", emulator.write_launcher(root, project.name, path))
    for w in project.warnings:
        print("  ! " + w)
    for x in broken:
        print(f"  ! scenario {x.source}: " + "; ".join(x.issues[:3]) + (" ..." if len(x.issues) > 3 else ""), file=sys.stderr)
    if broken and not args.lenient:
        print(f"Error: {len(broken)} scenario(s) do not match this HMI (exit code 4; use --lenient to ignore)", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
