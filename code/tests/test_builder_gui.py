"""The PySide6 builder window (layout file, jobs, window behaviour)."""
from pathlib import Path
import re
import shutil

import pytest

from nextion_parser import emulator

from helpers import SAMPLE, needs_sample

pytestmark = needs_sample


GUI_DIR = Path(emulator.__file__).parents[1] / "builder_gui"


def test_gui_ui_file_has_the_objects_app_py_uses():
    """main.ui (Qt Designer, English) defines every object app.py touches, with unique names."""
    import xml.etree.ElementTree as ET
    root = ET.parse(GUI_DIR / "main.ui").getroot()
    names = [w.get("name") for w in root.iter("widget")] + [l.get("name") for l in root.iter("layout")]
    assert len(names) == len(set(names)), "duplicate object names in main.ui"
    widgets = {w.get("name") for w in root.iter("widget")}
    app_src = (GUI_DIR / "app.py").read_text(encoding="utf-8")
    used = set(re.findall(r"\bw\.((?:edit|btn|label|combo|text)\w+)", app_src))
    assert used and used <= widgets, used - widgets
    langs = [i.find("property/string").text for i in root.find(".//widget[@name='comboLang']").findall("item")]
    assert langs == ["Magyar", "English"]                            # same order as app.LANGS
    assert not (GUI_DIR / "texts.json").exists()                     # the window is English only: texts live in main.ui


def test_gui_has_no_tk_leftovers():
    assert not (GUI_DIR / "uiloader.py").exists()
    assert "tkinter" not in "".join(p.read_text(encoding="utf-8") for p in GUI_DIR.glob("*.py")).lower()


def test_gui_job_runs_generation_and_streams_log(tmp_path):
    from nextion_parser.builder_gui import jobs
    shutil.copy(SAMPLE, tmp_path / "dev.HMI")
    chunks: list[str] = []
    res = jobs.run_generation(tmp_path / "dev.HMI", lang="en", emit=chunks.append)
    assert res.rc == 0 and res.launcher == tmp_path / "output" / "dev" / "index.html" and res.launcher.is_file()
    assert "coverage: overall" in res.log and "".join(chunks) == res.log
    assert '"lang": "en"' in (tmp_path / "output" / "dev" / "emulator" / "data.js").read_text(encoding="utf-8")
    bad = jobs.run_generation(tmp_path / "dev.HMI", out=tmp_path / "o2", screen="bogus")
    assert bad.rc != 0 and bad.launcher is None                     # a malformed --screen is reported, not raised
    assert jobs.run_generation(tmp_path / "missing.HMI").rc == 2


def test_gui_window_builds_and_generates(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")               # no display needed
    import time

    from PySide6 import QtWidgets
    from nextion_parser.builder_gui.app import BuilderWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    shutil.copy(SAMPLE, tmp_path / "w.HMI")
    win = BuilderWindow()
    assert win.w.windowTitle() == "Nextion emulator generator" and win.w.btnGenerate.text() == "▶ Generate"
    win.w.editHmi.setText(str(tmp_path / "w.HMI"))
    assert win.w.editOut.text() == str(tmp_path / "output" / "w")    # output follows the chosen file
    win.w.comboLang.setCurrentIndex(1)                               # English: default language of the generated emulator
    win.generate()
    end = time.time() + 120
    while win.busy and time.time() < end:
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()
    assert (tmp_path / "output" / "w" / "index.html").is_file() and win.w.btnOpenResult.isEnabled()
    assert "coverage: overall" in win.w.textLog.toPlainText()
    assert '"lang": "en"' in (tmp_path / "output" / "w" / "emulator" / "data.js").read_text(encoding="utf-8")
    win.w.editScreen.setText("bogus")                                # a failed run is reported and nothing can be opened
    win.generate()
    while win.busy and time.time() < end:
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()
    assert win.w.labelStatus.text().startswith("Failed") and not win.w.btnOpenResult.isEnabled()
