"""Tiny local web server for the generated emulator folders (standard library only, no package imports).

Besides serving the static files it exposes the scenarios folder to the emulator:
  GET  /<any prefix>/api/scenarios            -> [{"name": "x.json", "data": {...}}, ...]
  POST /<any prefix>/api/scenarios/<id>.json  -> writes the file (used by the recorder of the expert mode)
so recordings made in the expert emulator show up in the basic emulator without any manual file handling.
This file is also copied next to a portable package as ``start.py``.
"""
import argparse
import json
import re
import sys
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RESERVED = {"variables.json", "variables.discovered.json", "csv_profiles.json"}
API = re.compile(r"^(?:/.*)?/api/scenarios(?:/([^/]+\.json))?$")
SAFE = re.compile(r"^[\w.\-]+\.json$")


class Handler(SimpleHTTPRequestHandler):
    scenarios: Path = Path("scenarios")

    def log_message(self, fmt, *args):
        pass

    def _json(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        m = API.match(self.path.split("?")[0])
        if not m or m.group(1):
            return super().do_GET()
        items = []
        for f in sorted(self.scenarios.glob("*.json")):
            if f.name in RESERVED:
                continue
            try:
                items.append({"name": f.name, "data": json.loads(f.read_text(encoding="utf-8"))})
            except (OSError, ValueError):
                continue                                  # half-written / invalid file: skip
        self._json(200, items)

    def do_POST(self):
        m = API.match(self.path.split("?")[0])
        name = m.group(1) if m else None
        if not name or not SAFE.match(name) or name in RESERVED or name.startswith("."):
            return self._json(400, {"error": "bad name"})
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            json.loads(raw.decode("utf-8"))
        except ValueError:
            return self._json(400, {"error": "invalid JSON"})
        self.scenarios.mkdir(parents=True, exist_ok=True)
        (self.scenarios / name).write_bytes(raw)
        self._json(200, {"saved": name})


def run(root: Path, scenarios: Path | None = None, port: int = 8765, open_browser: bool = False,
        page: str = "index.html") -> None:
    root = root.resolve()
    Handler.scenarios = (scenarios or root / "scenarios").resolve()
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(root)))
    url = f"http://127.0.0.1:{srv.server_address[1]}/{page}"
    print(f"Serving {root}\nScenarios folder: {Handler.scenarios}\nOpen: {url}   (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Serve an emulator folder with a shared, auto-loaded scenarios folder")
    ap.add_argument("root", nargs="?", default=".", help="folder to serve (default: current)")
    ap.add_argument("--scenarios", help="scenarios folder (default: <root>/scenarios)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--open", action="store_true", help="open the page in the browser")
    a = ap.parse_args(argv)
    run(Path(a.root), Path(a.scenarios) if a.scenarios else None, a.port, a.open)
    return 0


if __name__ == "__main__":
    sys.exit(main())
