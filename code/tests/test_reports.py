"""HTML / JSON reports and their document model."""
import json
import re
import shutil

import pytest

from nextion_parser import emulator
from nextion_parser.reports import coverage as cov_r
from nextion_parser.reports import summary
from nextion_parser.reports import unused as unused_r

from helpers import SCN, needs_sample

pytestmark = needs_sample


def test_coverage_report(project, tmp_path):
    j, h, cov = cov_r.write(project, tmp_path)
    assert j.exists() and h.exists() and "<html" in h.read_text()
    assert cov["code"]["unknown"] == 0
    assert 0 < cov["overall_percent"] <= 100
    if shutil.which("node"):
        assert cov["runtime"]["available"] and cov["runtime"]["events"] > 400


def test_reports_are_english(project, tmp_path):
    cov_r.write(project, tmp_path / "c", SCN)
    unused_r.write(project, tmp_path / "u")
    summary.write_all(project, tmp_path / "s")
    hu_chars = re.compile("[áéíóöőúüűÁÉÍÓÖŐÚÜŰ]")
    for f in ("c/coverage.html", "u/unused.html", "u/unused.csv", "s/summary.html", "s/navigation.html", "s/navigation.mmd"):
        text = (tmp_path / f).read_text(encoding="utf-8-sig")
        assert not hu_chars.search(text) or f in ("s/summary.html",), f       # the summary shows project data (Program.s) verbatim
    text = (tmp_path / "c" / "coverage.html").read_text(encoding="utf-8")
    assert 'lang="en"' in text and "simulator coverage" in text
    assert "Scenarios (MCU simulation)" in text


def test_outputs(project, tmp_path):
    files = summary.write_all(project, tmp_path / "s")
    assert {f.name for f in files} == {"pages.json", "navigation.mmd", "navigation.html", "summary.html"}
    assert json.loads((tmp_path / "s" / "pages.json").read_text())["pages"]
    idx = emulator.generate(project, tmp_path / "e", start="pageMainAuto", screen=(800, 480), zoom="1")
    e = tmp_path / "e"
    for name in ("data.js", "nextion_core.js", "nextion_tools.js", "i18n.js", "help.html"):
        assert (e / name).exists(), name
    assert any((e / "img").iterdir())
    assert "__PROJECT__" not in idx.read_text()
    assert '"w": 800' in (e / "data.js").read_text()
    with pytest.raises(ValueError):
        emulator.parse_size("big")
    with pytest.raises(ValueError):
        emulator.generate(project, tmp_path / "x", start="nosuchpage")


def test_summary_is_html(project, tmp_path):
    summary.write_all(project, tmp_path)
    assert (tmp_path / "summary.html").exists() and not (tmp_path / "summary.md").exists()
    html = (tmp_path / "summary.html").read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>") and "pageMainAuto" in html and "Start-up program" in html
    assert "<table>" in html and "navigation.html" in html
    assert "## " not in html                                # no Markdown leftovers


def test_report_document_model_escapes_and_renders():
    from nextion_parser.reports.doc import Card, Cards, Details, Doc, Heading, Para, Table, code, esc, render, tag
    doc = Doc("T <x>", [Cards([Card("a<b", "90%", "s&s", 90)]), Heading("H"), Para("p", note=True),
                        Table(["h"], [[code("<i>")], [tag("ok")]], id="t", row_classes=["unused", None]),
                        Details("d", [Para("in")], open=True)])
    html = render(doc)
    assert "T &lt;x&gt;" in html and "a&lt;b" in html and "s&amp;s" in html and "<code>&lt;i&gt;</code>" in html
    assert "<tr class='unused'>" in html and "<table id='t'>" in html and "<details open>" in html and 'class="bar"' in html
    assert esc({"k": 1}) == "{&#x27;k&#x27;: 1}"


def test_coverage_tables_for_mismatches_and_unreachable(project, tmp_path):
    j, h, cov = cov_r.write(project, tmp_path / "c", SCN)
    html = h.read_text(encoding="utf-8")
    rs = cov["resources"]
    assert all({"page", "component", "attr", "component_size", "image_size"} <= set(m) for m in rs["image_dim_mismatch"])
    if rs["image_dim_mismatch"]:
        assert "<th>Component size</th>" in html and "<th>Image size</th>" in html
    rt = cov["runtime"]
    if rt.get("available") and rt["unreachable"]:
        assert "<th>Why it was not reached</th>" in html
        assert {x["page"] for x in rt["unreachable_info"]} == set(rt["unreachable"])
