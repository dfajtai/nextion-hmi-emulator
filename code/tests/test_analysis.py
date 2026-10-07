"""Analyses: discovery, scenarios, unused resources, templates."""
import json

import pytest

from nextion_parser import parser
from nextion_parser.analysis import coverage as cov_a
from nextion_parser.analysis import discover, scenario, unused
from nextion_parser.emulator import smoke
from nextion_parser.i18n import loc
from nextion_parser.reports import unused as unused_r

from helpers import SAMPLE_OLD, SAMPLE, SCN, TEMPLATES, needs_node, needs_sample

pytestmark = needs_sample


def test_classify():
    assert cov_a.classify("page pageMenu") == ("supported", "page")
    assert cov_a.classify("if(a.val==1)") == ("supported", "if")
    assert cov_a.classify("t0.txt=\"x\"") == ("supported", "assign")
    assert cov_a.classify("delay 100")[0] == "ignored"
    assert cov_a.classify("cls 0")[0] == "unknown"


def test_support_tables_match_core():
    core = (TEMPLATES / "nextion_core.js").read_text(encoding="utf-8")
    for cmd in cov_a.SUPPORTED_CMDS | cov_a.IGNORED_CMDS:
        assert cmd in core, f"{cmd} is not handled by the interpreter"


def test_discover_finds_mcu_inputs(project):
    refs = {v["ref"]: v for v in discover.build(project)}
    cl = refs["pageMainAuto.charge_level.val"]
    assert cl["confidence"] == "high" and cl["scope"] == "global" and 80 in cl["test_values"]
    assert "pageMainAuto.charging.val" in refs
    assert "pageMainAuto.tcharge.txt" not in refs          # written by the code -> not an external input


def test_variables_override(project):
    merged = discover.merge(discover.build(project), {"pageMainAuto.charge_level.val": {"label": {"hu": "Töltöttség", "en": "Charge level"}},
                                                       "pageMainAuto.lang.val": {"hidden": True}})
    by = {v["ref"]: v for v in merged}
    assert loc(by["pageMainAuto.charge_level.val"]["label"], "en") == "Charge level"
    assert "pageMainAuto.lang.val" not in by


def test_loc_helper():
    assert loc("x") == "x" and loc(None) == ""
    assert loc({"hu": "szia", "en": "hi"}, "hu") == "szia" and loc({"hu": "szia", "en": "hi"}, "en") == "hi"
    assert loc({"hu": "szia"}, "en") == "szia"             # falls back to any available language


@pytest.mark.skipif(not SCN.is_dir(), reason="no test scenarios")
def test_scenarios_validate(project):
    scns = scenario.load_dir(project, SCN)
    assert len(scns) >= 10 and all(not s.issues for s in scns)
    bad = scenario.Scenario("x", "x", "", "pageMainAuto", [{"set": {"pageMainAuto.nope.val": 1}}, {"goto": "nope"}, {"foo": 1}], "x")
    issues = scenario.validate(project, bad, "pageMainAuto")
    assert len(issues) == 3 and all(i.isascii() for i in issues)


@pytest.mark.skipif(not SCN.is_dir(), reason="no test scenarios")
def test_sample_scenarios_are_bilingual(project):
    for s in scenario.load_dir(project, SCN):
        assert isinstance(s.name, dict) and s.name.get("hu") and s.name.get("en"), s.id
        for st in s.steps:
            if isinstance(st.get("say"), dict):
                assert st["say"].get("hu") and st["say"].get("en"), s.id
    v = json.loads((SCN / "variables.json").read_text(encoding="utf-8"))
    assert all(isinstance(o["label"], dict) and o["label"].get("en") for o in v.values() if "label" in o)


@needs_node
@pytest.mark.skipif(not SCN.is_dir(), reason="no test scenarios")
def test_scenarios_run_headless(project, tmp_path):
    cov = cov_a.build(project, SCN, smoke.runtime(project, tmp_path / "w", SCN))["scenarios"]
    assert cov["count"] >= 10 and cov["percent"] == 100.0
    assert "pageStat2" in cov["pages_visited"]


def test_unused_report(project, tmp_path):
    rep = unused.analyze(project)
    s = rep["summary"]
    assert s["images_total"] == len(project.images) and s["images_unused"] >= 1
    assert all(x["status"] != "unused" for x in rep["images"] if x["refs"])
    assert s["hmi_dead_bytes"] >= 0 and rep["fonts"][0]["bytes"] > 0
    if SAMPLE_OLD.exists():                                     # a file saved by an older Editor keeps deleted ("dead") sections
        assert unused.analyze(parser.load(SAMPLE_OLD))["summary"]["hmi_dead_bytes"] > 0
    # images assigned literally in the code (pbattery.pic=23..34) count as used
    used = {x["id"] for x in rep["images"] if x["status"] == "used"}
    assert {23, 25, 27, 29, 31, 34} <= used
    paths = unused_r.write(project, tmp_path)
    assert all(p.exists() for p in paths.values())
    assert "unused" in paths["html"].read_text()
    assert (tmp_path / "img").is_dir()
    assert paths["csv"].read_text(encoding="utf-8-sig").splitlines()[0] == "kind;id;name;status;size_bytes;details"


def test_resources_block_agrees_with_unused_report(project):
    ua = unused.analyze(project)["summary"]
    rs = cov_a.static_resources(project)
    assert rs["images_available"] == ua["images_total"] and rs["images_unused"] == ua["images_unused"]
    assert rs["images_used"] + rs["images_unused"] + rs["images_uncertain"] == ua["images_total"]
    assert "(oldal)" not in json.dumps(unused.analyze(project))


def test_variables_template_and_csv_profile_guess(project, tmp_path):
    from nextion_parser.analysis import csvprofile
    from nextion_parser.reports import discover as discover_report
    found = discover.build(project)
    tpl = discover.variables_template(found)
    assert set(tpl) == {v["ref"] for v in found} and all(t["label"]["en"] and t["group"]["en"] for t in tpl.values())
    assert tpl["pageMainAuto.charge_level.val"]["presets"]                       # probe values from the code become presets
    merged = {v["ref"]: v for v in discover.merge(found, tpl)}                    # a template is a valid variables.json overlay
    assert set(merged) == set(tpl)
    prof = csvprofile.guess_profile(project)["stats"]
    hand = json.loads((SAMPLE.parent / "scenarios" / "csv_profiles.json").read_text(encoding="utf-8"))["stats"]
    assert {k: prof[k] for k in ("page", "path", "quantity", "mean", "sd", "cv")} == {k: hand[k] for k in ("page", "path", "quantity", "mean", "sd", "cv")}
    assert prof["wave"]["ref"] == hand["wave"]["ref"]
    files = discover_report.write(project, tmp_path)
    assert {f.name for f in files} == {"variables.discovered.json", "variables.template.json", "csv_profiles.template.json"}


def test_csv_profile_guess_gives_up_without_a_statistics_page():
    from nextion_parser.analysis import csvprofile
    from nextion_parser.parser import Page, Project
    p = Project.__new__(Project)
    p.pages, p.start_page = [], None
    assert csvprofile.guess_profile(p) is None


def test_example_picker_has_generic_fallbacks():
    from nextion_parser.emulator.examples import pick_examples
    from nextion_parser.parser import Project
    p = Project.__new__(Project)
    p.pages = []
    assert pick_examples(p, {"start": "p1", "variables": []}) == {
        "page": "p1", "other_page": "p1", "ref": "p1.component.val", "btn": "button", "wave": None}
