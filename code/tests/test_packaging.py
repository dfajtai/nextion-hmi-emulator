"""Portable basic package, helper server and scenario update scripts."""
import json
import subprocess

import pytest

from nextion_parser import emulator
from nextion_parser.cli import main

from helpers import SAMPLE, SCN, needs_node, needs_sample

pytestmark = needs_sample


def test_portable_basic_package(project, tmp_path):
    rc = main(["portable", str(SAMPLE), "-o", str(tmp_path / "p"), "--scenarios", str(SCN)])
    assert rc == 0
    p = tmp_path / "p"
    for f in ("index.html", "data.js", "nextion_core.js", "nextion_tools.js", "i18n.js", "scenarios/README.txt"):
        assert (p / f).is_file(), f
    assert not (p / "help.html").exists()
    assert list((p / "scenarios").glob("*.json")) == []            # empty scenarios folder
    data = (p / "data.js").read_text(encoding="utf-8")
    assert '"portable": true' in data and '"scenarios": []' in data and '"reports": []' in data
    html = (p / "index.html").read_text(encoding="utf-8")
    assert "showDirectoryPicker" in html and "DATA.portable?'simple'" in html


@needs_node
def test_portable_locked_to_simple_mode_in_js(project, tmp_path):
    emulator.generate(project, tmp_path, scenario_dir=SCN, portable=True)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    # the mode selector is hidden and the expert mode cannot be requested through the URL
    assert "$('mode').closest('label').hidden=true" in html
    assert "setMode(DATA.portable?'simple'" in html


def test_serve_api_lists_and_saves_scenarios(tmp_path):
    import threading
    import urllib.request
    from functools import partial
    from http.server import ThreadingHTTPServer

    from nextion_parser.emulator import serve
    root = tmp_path / "r"
    (root / "scenarios").mkdir(parents=True)
    (root / "scenarios" / "a.json").write_text('{"name":"A","steps":[]}', encoding="utf-8")
    (root / "scenarios" / "variables.json").write_text("[]", encoding="utf-8")
    (root / "index.html").write_text("hi", encoding="utf-8")
    serve.Handler.scenarios = root / "scenarios"
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(serve.Handler, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        items = json.load(urllib.request.urlopen(base + "/emulator/api/scenarios"))
        assert [i["name"] for i in items] == ["a.json"]                  # reserved files are not listed
        req = urllib.request.Request(base + "/portable/api/scenarios/b.json", data=b'{"steps":[]}', method="POST")
        assert urllib.request.urlopen(req).status == 200
        assert (root / "scenarios" / "b.json").is_file()
        bad = urllib.request.Request(base + "/api/scenarios/..%2Fevil.json", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(bad)
        assert urllib.request.urlopen(base + "/index.html").read() == b"hi"
    finally:
        srv.shutdown()


def test_update_scenarios_script_bundles_and_imports(tmp_path):
    root = tmp_path / "o"
    for d in ("emulator", "portable"):
        (root / d).mkdir(parents=True)
        (root / d / "index.html").write_text("x")
        (root / d / "data.js").write_text("x")
    emulator.write_scripts(root)
    scen = root / "portable" / "scenarios"
    scen.mkdir()
    (scen / "a.json").write_text('{"name":"A","steps":[{"say":"hi"}]}', encoding="utf-8")
    (scen / "bad.json").write_text("{oops", encoding="utf-8")
    (scen / "variables.json").write_text("[]", encoding="utf-8")
    dl = tmp_path / "Downloads"                                             # recordings downloaded by the expert emulator
    dl.mkdir()
    (dl / "rec1.json").write_text('{"name":"R","steps":[]}', encoding="utf-8")
    (dl / "other_tool.json").write_text('{"setting": 1}', encoding="utf-8")   # unrelated JSON must not be imported
    r = subprocess.run(["python3", str(root / "scripts" / "update_scenarios.py"), str(dl)], capture_output=True, text=True)
    assert r.returncode == 1 and "bad.json" in r.stdout                       # invalid file reported, others still written
    assert (scen / "rec1.json").is_file() and not (scen / "other_tool.json").exists()
    for d in ("emulator", "portable"):
        js = (root / d / "scenarios.js").read_text(encoding="utf-8")
        assert js.startswith("window.NX_SCENARIOS=") and '"a.json"' in js and '"rec1.json"' in js and "variables.json" not in js
    for f in ("update_scenarios.bat", "update_scenarios.sh"):
        assert (root / "scripts" / f).is_file()
