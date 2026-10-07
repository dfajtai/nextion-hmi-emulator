"""Tests that run against the sample project (sample/bioscale_research_old.HMI, saved by Nextion Editor 1.6.8.1)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from nextion_parser import emulator, parser
from nextion_parser.analysis import coverage as cov_a
from nextion_parser.analysis import discover, navigation, scenario, unused
from nextion_parser.emulator import smoke
from nextion_parser.reports import coverage as cov_r
from nextion_parser.reports import summary
from nextion_parser.reports import unused as unused_r
from nextion_parser.cli import main
from nextion_parser.i18n import loc

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample"
SAMPLE = SAMPLE_DIR / "bioscale_research_old.HMI"
SAMPLE_NEW = SAMPLE_DIR / "bioscale_research_new.HMI"           # the same project re-saved by Editor 1.6.8.2
SCN = Path(__file__).parent / "fixtures" / "scenarios"
DATA_DIR = SAMPLE.parent / "data"
TEMPLATES = Path(emulator.__file__).parent / "assets"
pytestmark = pytest.mark.skipif(not SAMPLE.exists(), reason="no sample HMI")
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")


@pytest.fixture(scope="module")
def project():
    return parser.load(SAMPLE)


def gen(project, tmp_path, **kw):
    emulator.generate(project, tmp_path, scenario_dir=SCN, **kw)
    return (tmp_path / "index.html").read_text(encoding="utf-8")


def script_of(html: str) -> str:
    return re.findall(r"<script>(.*?)</script>", html, re.S)[-1]


# ------------------------------------------------------------------ parser
def test_directory_and_pages(project):
    names = {p.name for p in project.pages}
    assert {"pageMainAuto", "pageMenu", "pageCal"} <= names
    assert project.pages[0].name == "pageMainAuto" and project.start_page == "pageMainAuto"
    assert (project.width, project.height) == (480, 272)
    assert project.sections["live"] + project.sections["deleted"] == project.sections["total"]
    assert not project.warnings                          # object counts match the page headers


def test_images_follow_resource_order(project):
    # the pic id is the position in the main.HMI resource list; the sizes confirm it (>95 % match)
    rs = cov_a.static_resources(project)
    assert rs["image_dim_percent"] > 95
    assert not rs["images_missing"] and not rs["fonts_missing"]
    assert all(im.data[:4] == b"\x89PNG" for im in project.images.values())


def test_navigation_edge(project):
    edges, _ = navigation.navigation(project)
    assert "bcalibration.down" in edges[("pageMenu", "pageCal")]


def test_program(project):
    assert "int sys0" in project.program


def test_invalid_file_is_rejected(tmp_path):
    bad = tmp_path / "bad.HMI"
    bad.write_bytes(b"\x00" * 64)
    with pytest.raises(ValueError, match="Not a valid"):
        parser.load(bad)


# ------------------------------------------------------------------ coverage / classification
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


# ------------------------------------------------------------------ outputs / CLI
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


def test_cli(tmp_path):
    assert main(["all", str(SAMPLE), "-o", str(tmp_path), "--screen", "800x480", "--lang", "en"]) == 0
    assert (tmp_path / "coverage" / "coverage.html").exists()
    assert '"lang": "en"' in (tmp_path / "emulator" / "data.js").read_text(encoding="utf-8")
    assert main(["emulator", str(SAMPLE), "-o", str(tmp_path / "x"), "--screen", "bad"]) == 2
    assert main(["emulator", str(tmp_path / "missing.HMI")]) == 2


def test_cli_all_generates_emulator_last(project, tmp_path):
    assert main(["all", str(SAMPLE), "-o", str(tmp_path)]) == 0
    data = (tmp_path / "emulator" / "data.js").read_text(encoding="utf-8")
    for rep in ("coverage/coverage.html", "unused/unused.html", "summary/navigation.html"):
        assert rep in data                                  # the emulator is generated last, so every report is in the menu
    assert '"key": "coverage"' in data


def test_summary_is_html(project, tmp_path):
    summary.write_all(project, tmp_path)
    assert (tmp_path / "summary.html").exists() and not (tmp_path / "summary.md").exists()
    html = (tmp_path / "summary.html").read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>") and "pageMainAuto" in html and "Start-up program" in html
    assert "<table>" in html and "navigation.html" in html
    assert "## " not in html                                # no Markdown leftovers


# ------------------------------------------------------------------ discovery / scenarios
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


def test_emulator_embeds_scenarios(project, tmp_path):
    gen(project, tmp_path)
    data = (tmp_path / "data.js").read_text(encoding="utf-8")
    assert '"scenarios"' in data and '"variables"' in data and '"csvProfiles"' in data and "pageStat1.xmean.val" in data


# ------------------------------------------------------------------ unused resources
def test_unused_report(project, tmp_path):
    rep = unused.analyze(project)
    s = rep["summary"]
    assert s["images_total"] == len(project.images) and s["images_unused"] >= 1
    assert all(x["status"] != "unused" for x in rep["images"] if x["refs"])
    assert s["hmi_dead_bytes"] > 0 and rep["fonts"][0]["bytes"] > 0
    # images assigned literally in the code (pbattery.pic=23..34) count as used
    used = {x["id"] for x in rep["images"] if x["status"] == "used"}
    assert {23, 25, 27, 29, 31, 34} <= used
    paths = unused_r.write(project, tmp_path)
    assert all(p.exists() for p in paths.values())
    assert "unused" in paths["html"].read_text()
    assert (tmp_path / "img").is_dir()
    assert paths["csv"].read_text(encoding="utf-8-sig").splitlines()[0] == "kind;id;name;status;size_bytes;details"


# ------------------------------------------------------------------ CSV tools / core (Node)
@needs_node
@pytest.mark.skipif(not (DATA_DIR / "meresek.csv").exists(), reason="no sample CSV")
def test_csv_scenarios(project, tmp_path):
    gen(project, tmp_path)
    r = subprocess.run(["node", str(Path(__file__).parent / "csv_check.js"), str(tmp_path / "data.js"), str(tmp_path / "nextion_core.js"),
                        str(tmp_path / "nextion_tools.js"), str(DATA_DIR / "meresek.csv"), str(DATA_DIR / "akku_idosor.csv")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    st = out["stats"]
    assert st["problems"] == 0 and not st["scnErr"] and st["n"] == 18 and st["grp"] == "B-csoport" and st["wave"] == 18
    assert 1650 < st["mean"] < 1760 and 40 < st["sd"] < 110
    se = out["series"]
    assert se["problems"] == 0 and se["unknown"] == [] and se["weight"] == 1520 and se["ms"] == 13600
    assert out["parse"]["semi"] == ["1,5", "2"] and out["parse"]["tab"] == "\t" and out["parse"]["quoted"] == ["x,y", "2"]
    assert out["num"][0] == 1.5 and out["num"][1] == 1.5 and out["num"][2] is None
    assert out["sd"] == [8, 5, 2.138]                       # sample standard deviation (n-1)
    # generated names / captions are bilingual objects
    assert out["names"]["stats"]["en"].startswith("CSV statistics") and out["names"]["stats"]["hu"].startswith("CSV statisztika")
    assert out["names"]["series"]["en"] == "CSV time series"


@needs_node
@pytest.mark.skipif(not SCN.is_dir(), reason="no test scenarios")
def test_language_scenario_switches_to_english(project, tmp_path):
    gen(project, tmp_path)
    js = """
const fs=require('fs');const DATA=new Function(fs.readFileSync('data.js','utf8')+';return DATA;')();
const {createCore}=require('./nextion_core.js');
const core=createCore(DATA,{log(){},render(){},changed(){}});
const r=core.runScenarioSync(DATA.scenarios.find(s=>s.id==='05_nyelv_angol'));
const S=core.S().pageMainAuto;
console.log(JSON.stringify({bdel:S.bdel.txt,t1:S.t1.txt,problems:r.problems,cur:core.cur()}));
"""
    r = subprocess.run(["node", "-e", js], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"bdel": "DELETE", "t1": "Weight", "problems": 0, "cur": "pageMainAuto"}


@needs_node
def test_idle_timer_jump_can_be_blocked(project, tmp_path):
    gen(project, tmp_path)
    js = """
const fs=require('fs');const DATA=new Function(fs.readFileSync('data.js','utf8')+';return DATA;')();
const {createCore}=require('./nextion_core.js');
function run(block){
  const core=createCore(DATA,{log(){},render(){},changed(){}});
  core.options.timerPageJumps=!block;
  core.boot('pageMainAuto');core.setValue('pageMainAuto.sleep_sec.val',2);
  core.goto('pageMenu');for(let i=0;i<120;i++){core.tick(50);if(core.hasQueue())core.flush();}   // 6 s of inactivity
  return core.cur();
}
console.log(JSON.stringify({allowed:run(false),blocked:run(true)}));
"""
    r = subprocess.run(["node", "-e", js], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"allowed": "pageMainAuto", "blocked": "pageMenu"}


@needs_node
def test_core_messages_are_localizable(project, tmp_path):
    gen(project, tmp_path)
    js = """
const fs=require('fs');const DATA=new Function(fs.readFileSync('data.js','utf8')+';return DATA;')();
const {createCore}=require('./nextion_core.js');
const msgs=[];
const en=createCore(DATA,{log(t){msgs.push(t);},render(){},changed(){}});
en.boot('pageMainAuto');en.applyStep({cmd:'nosuch.obj.val=1'});
const hu=createCore(DATA,{log(t){msgs.push(t);},render(){},changed(){},t:(k,v)=>'HU:'+k});
hu.boot('pageMainAuto');hu.applyStep({cmd:'nosuch.obj.val=1'});
console.log(JSON.stringify(msgs.filter(m=>/unknown|core\\./.test(m))));
"""
    r = subprocess.run(["node", "-e", js], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    msgs = json.loads(r.stdout)
    assert any(m.startswith("? unknown target") for m in msgs) and any(m == "HU:core.unknownTarget" for m in msgs)


# ------------------------------------------------------------------ GUI structure
@needs_node
def test_emulator_script_syntax(project, tmp_path):
    html = gen(project, tmp_path)
    (tmp_path / "ui.js").write_text(script_of(html), encoding="utf-8")
    for f in ("ui.js", "nextion_core.js", "nextion_tools.js", "i18n.js", "data.js"):
        r = subprocess.run(["node", "--check", str(tmp_path / f)], capture_output=True, text=True)
        assert r.returncode == 0, f"{f}: {r.stderr[:300]}"
    assert 'id="mode"' in html and 'id="scnfile"' in html


def test_no_lost_functions_and_dangling_handlers(project, tmp_path):
    js = script_of(gen(project, tmp_path))
    defined = set(re.findall(r"function\s+(\w+)", js))
    must = {"slug", "download", "addScenarioObj", "recStart", "recStop", "recDiscard", "recSave", "recAppend", "editScenario",
            "openStepEdit", "renderRec", "recPush", "recAddDelay", "playScn", "pauseScn", "stepForward", "prevStep", "gotoStep",
            "selectScn", "loadFiles", "openCsv", "setCaption", "warn", "toggleHist", "applySize", "showClick", "visSig", "boot",
            "applyLang", "applyStatic", "renderCaption", "buildReportsMenu", "R"}
    assert not (must - defined), sorted(must - defined)
    for fn in re.findall(r"\.onclick=(\w+)[;,}]", js):
        assert fn in defined, fn                            # every named onclick handler exists


def test_header_is_clean_and_display_controls_in_own_block(project, tmp_path):
    html = gen(project, tmp_path)
    header = re.search(r"<header>(.*?)</header>", html, re.S).group(1)
    for gone in ('id="loadbtn"', 'id="sw"', 'id="zoom"', 'id="dbg"', 'id="timerjump"', 'id="sizereset"', 'id="start"'):
        assert gone not in header, gone
    for kept in ('id="mode"', 'id="goto"', 'id="reset"', 'id="helplink"', 'id="repmenu"', 'id="lang"'):
        assert kept in header
    scn = re.search(r'<div class="card" id="scncard">(.*?)<div id="scndesc"', html, re.S).group(1)
    assert 'id="loadbtn"' in scn and 'id="scnfile"' in scn
    disp = re.search(r'<div class="card expert" id="dispcard"[^>]*>(.*?)</div>\n</aside>', html, re.S).group(1)
    for ctl in ('id="sw"', 'id="sh"', 'id="zoom"', 'id="dbg"', 'id="timerjump"', 'id="sizereset"'):
        assert ctl in disp, ctl
    assert 'data-collapsed="1"' in html.split('id="dispcard"')[1][:60]


def test_layout_grid_and_cards(project, tmp_path):
    html = gen(project, tmp_path)
    assert 'grid-template-areas:"scr side" "below side"' in html and 'grid-template-areas:"scr" "side" "below"' in html
    assert "clamp(320px,34vw,540px)" in html and "new ResizeObserver" in html and "$('left').clientWidth" in html
    main_html = re.search(r"<main>(.*)</main>", html, re.S).group(1)
    assert main_html.index('id="below"') > main_html.index("<aside>") and main_html.index('id="varcard"') > main_html.index('id="below"')
    assert "card.classList.toggle('collapsed'" in html
    assert 'id="globcard" data-collapsed="1"' in html and 'id="simcard"' not in html and "buildSim" not in html
    assert "input[type=checkbox]" in html


def test_player_and_recorder_behaviour_hooks(project, tmp_path):
    js = script_of(gen(project, tmp_path))
    assert "function visSig" in js and "visSig()!==lastSig" in js and "else render();},50)" not in js     # no constant re-render
    assert "function finishPending" in js and "function cancelPending" in js and "play.stepT=setTimeout" in js
    assert "function markDirty" in js and "gotoStep(play.k>=n?0:play.k)" in js and "play.dirty||play.k===0&&play.state!=='play'" in js
    assert "const PREROLL=" in js and "setTimeout(playTop,Math.round(PREROLL/" in js and "setTimeout(begin,Math.round(PREROLL*0.7))" in js
    assert "!rec.on&&!rec.steps.length)rp.value=nx.cur()" in js and "nx.boot($('recpage').value)" in js
    assert "recreal').checked" in js and "function recAddDelay" in js
    assert "classList.contains('mode-expert')" in js        # name label / tooltip only in expert mode
    assert "/[\\u0300-\\u036f]/g" in js                     # readable escape in slug()
    assert 'id="recstop"' not in script_of(gen(project, tmp_path))


# ------------------------------------------------------------------ i18n
def test_gui_dictionaries_are_complete(project, tmp_path):
    html = gen(project, tmp_path)
    src = (TEMPLATES / "i18n.js").read_text(encoding="utf-8")

    def keys(lang):
        body = re.search(r"\n  " + lang + r": \{(.*?)\n  \},", src, re.S).group(1)
        return set(re.findall(r'"([\w.]+)":', body))

    hu, en = keys("hu"), keys("en")
    assert hu == en, (sorted(hu ^ en))                      # both languages define exactly the same keys
    js = script_of(html)
    used = set(re.findall(r'data-i(?:h|t|p)?="([\w.]+)"', html))
    used |= set(re.findall(r"\bt\('([\w.]+)'", js)) | set(re.findall(r"key:'([\w.]+)'", js))
    used |= set(re.findall(r"""data-i\w*="([\w.]+)\"""", html))
    prefixes = {"cap.badge.": ("step", "aux", "info"), "scn.btn.": ("play", "pause", "resume"), "rec.hint": ("0", "1", "2", "3"),
                "rep.": ("coverage", "unused", "navigation", "summary")}
    for p, suffixes in prefixes.items():
        for suf in suffixes:
            used.add(p + suf)
    used -= {"cap.badge.", "scn.btn.", "rec.hint", "rep.", "type."}      # prefixes of dynamically built keys (their concrete keys are checked above/below)
    used |= {f"type.{n}" for n in (0, 1, 54, 56, 57, 59, 98, 106, 109, 112, 116)}
    missing = sorted(k for k in used if k not in hu)
    assert not missing, missing
    core_keys = set(re.findall(r'tr\("(\w+)"', (TEMPLATES / "nextion_core.js").read_text(encoding="utf-8")))
    assert {f"core.{k}" for k in core_keys} <= hu           # every core message can be localized


def test_gui_has_language_switch_and_default(project, tmp_path):
    html = gen(project, tmp_path, lang="en")
    assert 'id="lang"' in html and '<option value="hu">Magyar</option><option value="en">English</option>' in html
    assert '"lang": "en"' in (tmp_path / "data.js").read_text(encoding="utf-8")
    js = script_of(html)
    assert "function applyLang" in js and "lsSet('nx_lang'" in js and "new URLSearchParams(location.search).get('lang')" in js
    assert not re.search("[áéíóöőúüűÁÉÍÓÖŐÚÜŰ]", js), "GUI script should hold no hard-coded Hungarian text (it belongs in i18n.js)"


@needs_node
def test_t_and_loc_run_in_node():
    js = """
const {t,loc,setLang,I18N}=require('./i18n.js');
setLang('en');const a=t('cap.stepn',{n:2,N:5});
setLang('hu');const b=t('cap.stepn',{n:2,N:5});
const c=t('cap.scn',{name:{hu:'Név',en:'Name'},desc:'d'});
setLang('en');const d=t('cap.scn',{name:{hu:'Név',en:'Name'},desc:'d'});
console.log(JSON.stringify({a,b,c,d,k:t('no.such.key'),l:loc({hu:'x'}),m:Object.keys(I18N.hu).length===Object.keys(I18N.en).length}));
"""
    r = subprocess.run(["node", "-e", js], cwd=TEMPLATES, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"a": "step 2 / 5", "b": "lépés 2 / 5", "c": "Név – d", "d": "Name – d", "k": "no.such.key", "l": "x", "m": True}


def test_help_is_bilingual(project, tmp_path):
    gen(project, tmp_path)
    t = (tmp_path / "help.html").read_text(encoding="utf-8")
    hu_ids = ("attekintes", "gyors", "modok", "kijelzo", "lejatszo", "felirat", "rogzito", "szerkesztes", "csv", "valtozok",
              "formatum", "nyelv", "riportok", "url", "hibak", "projekt")
    en_ids = ("overview", "quick", "modes", "display", "player", "caption", "recorder", "editing", "csvimport", "variables",
              "format", "language", "reports", "urls", "trouble", "project")
    for anchor in hu_ids + en_ids:
        assert f'id="{anchor}"' in t and f'href="#{anchor}"' in t, anchor     # every chapter + its table-of-contents link
    assert 'id="hlang"' in t and 'html[lang="hu"] .lang-en' in t and "nx_lang" in t
    assert "01_akku_lemerules" in t and "Battery discharge" in t and "Akku lemerülése" in t   # localized project part
    # the help refers to the real GUI labels (both languages)
    i18n = (TEMPLATES / "i18n.js").read_text(encoding="utf-8")
    for label in ("Szerkesztés a rögzítőben", "Folytatás a végétől", "Rögzítés indítása", "Rögzítés leállítása", "Alap méret"):
        assert label in t and label in i18n, label
    for label in ("Edit in the recorder", "Continue from the end", "Start recording", "Stop recording", "Default size"):
        assert label in t and label in i18n, label
    ui = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert 'id="helplink" href="help.html"' in ui


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


def test_all_writes_launcher_and_portable(tmp_path):
    out = tmp_path / "o"
    assert main(["all", str(SAMPLE), "-o", str(out), "--scenarios", str(SCN)]) == 0
    idx = (out / "index.html").read_text(encoding="utf-8")
    for href in ("emulator/index.html", "portable/index.html", "coverage/coverage.html"):
        assert href in idx
    assert (out / "portable" / "serve.py").is_file() and (out / "portable" / "start.bat").is_file() and (out / "portable" / "update_scenarios.py").is_file()
    assert (out / "scripts" / "update_scenarios.py").is_file() and (out / "portable" / "scenarios").is_dir() and not (out / "scenarios").exists()
    assert (out / "emulator" / "scenarios.js").is_file() and (out / "portable" / "scenarios.js").is_file()


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


def test_emulator_has_server_sync(project, tmp_path):
    html = gen(project, tmp_path)
    assert "api/scenarios" in html and "syncServer" in html and "rec.info.saved.server" in html


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


def test_resources_block_agrees_with_unused_report(project):
    ua = unused.analyze(project)["summary"]
    rs = cov_a.static_resources(project)
    assert rs["images_available"] == ua["images_total"] and rs["images_unused"] == ua["images_unused"]
    assert rs["images_used"] + rs["images_unused"] + rs["images_uncertain"] == ua["images_total"]
    assert "(oldal)" not in json.dumps(unused.analyze(project))


def test_broken_scenario_gives_exit_code_but_still_generates(tmp_path, capsys):
    scn = tmp_path / "scn"
    scn.mkdir()
    (scn / "bad.json").write_text('{"name":"bad","steps":[{"click":"doesNotExist"},{"goto":"noSuchPage"}]}', encoding="utf-8")
    out = tmp_path / "o"
    assert main(["emulator", str(SAMPLE), "-o", str(out), "--scenarios", str(scn)]) == 4
    assert "bad.json" in capsys.readouterr().err
    assert (out / "index.html").is_file()                               # generated anyway
    assert main(["emulator", str(SAMPLE), "-o", str(out), "--scenarios", str(scn), "--lenient"]) == 0


def test_launcher_stamps_the_source_hmi(tmp_path):
    out = tmp_path / "o"
    assert main(["all", str(SAMPLE), "-o", str(out), "--scenarios", str(SCN)]) == 0
    idx = (out / "index.html").read_text(encoding="utf-8")
    assert SAMPLE.name in idx and "sha256" in idx and "Generated" in idx


def test_report_document_model_escapes_and_renders():
    from nextion_parser.reports.doc import Card, Cards, Details, Doc, Heading, Para, Table, code, esc, render, tag
    doc = Doc("T <x>", [Cards([Card("a<b", "90%", "s&s", 90)]), Heading("H"), Para("p", note=True),
                        Table(["h"], [[code("<i>")], [tag("ok")]], id="t", row_classes=["unused", None]),
                        Details("d", [Para("in")], open=True)])
    html = render(doc)
    assert "T &lt;x&gt;" in html and "a&lt;b" in html and "s&amp;s" in html and "<code>&lt;i&gt;</code>" in html
    assert "<tr class='unused'>" in html and "<table id='t'>" in html and "<details open>" in html and 'class="bar"' in html
    assert esc({"k": 1}) == "{&#x27;k&#x27;: 1}"


def test_restart_resets_the_scenario_too(project, tmp_path):
    html = gen(project, tmp_path)
    handler = re.search(r"\$\('reset'\)\.onclick=\(\)=>\{(.*?)\n\};", html, re.S).group(1)
    assert "stopScn()" in handler and "boot()" in handler and "play.scn&&!rec.on" in handler


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


def test_easy_generator_single_file(tmp_path):
    import zipapp
    stage = tmp_path / "stage"
    shutil.copytree(Path(emulator.__file__).parents[1], stage / "nextion_parser", ignore=shutil.ignore_patterns("__pycache__"))
    pyz = tmp_path / "work" / "nextion-generator.pyz"
    pyz.parent.mkdir()
    zipapp.create_archive(stage, pyz, main="nextion_parser.easy:run")
    r = subprocess.run(["python3", str(pyz)], cwd=tmp_path, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 2 and "No .HMI file found" in r.stderr                       # nothing next to it
    shutil.copy(SAMPLE, pyz.parent / "device.HMI")
    r = subprocess.run(["python3", str(pyz)], cwd=tmp_path, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr
    out = pyz.parent / "output" / "device"
    for f in ("index.html", "emulator/index.html", "portable/index.html", "coverage/coverage.html", "portable/start.bat"):
        assert (out / f).is_file(), f
    assert "device.HMI" in (out / "index.html").read_text(encoding="utf-8")


@pytest.mark.skipif(not SAMPLE_NEW.exists(), reason="no sample saved by the newer Editor")
def test_editor_1_6_8_2_file_is_read_identically(project):
    """The same project saved by Editor 1.6.8.1 and 1.6.8.2 must give the same model (only the dead sections differ)."""
    new = parser.load(SAMPLE_NEW)
    assert (new.width, new.height, new.start_page) == (project.width, project.height, project.start_page)
    assert [p.name for p in new.pages] == [p.name for p in project.pages]
    for a, b in zip(project.pages, new.pages):
        assert a.page.attrs == b.page.attrs and a.code == b.code
        assert [(c.attrs, c.code) for c in a.comps] == [(c.attrs, c.code) for c in b.comps]
    assert {i: im.data for i, im in project.images.items()} == {i: im.data for i, im in new.images.items()}
    assert new.program == project.program and not new.warnings
    assert emulator.build_data(new)["pages"] == emulator.build_data(project)["pages"]


# ------------------------------------------------------------------ builder GUI (PySide6, Qt Designer .ui file)
GUI_DIR = Path(emulator.__file__).parents[1] / "builder_gui"


def test_gui_ui_file_and_texts_are_consistent():
    """main.ui (Qt Designer) and texts.json agree: every text targets an existing widget and exists in both languages."""
    import xml.etree.ElementTree as ET
    root = ET.parse(GUI_DIR / "main.ui").getroot()
    names = [w.get("name") for w in root.iter("widget")] + [l.get("name") for l in root.iter("layout")]
    assert len(names) == len(set(names)), "duplicate object names in main.ui"
    widgets = {w.get("name"): w.get("class") for w in root.iter("widget")}
    texts = json.loads((GUI_DIR / "texts.json").read_text(encoding="utf-8"))
    for group in ("labels", "placeholders"):
        for name, spec in texts[group].items():
            assert name in widgets, f"{group}: {name} is not a widget of main.ui"
            assert spec.get("hu") and spec.get("en"), name
    for name, spec in list(texts["messages"].items()) + [("window", texts["window"])]:
        assert spec.get("hu") and spec.get("en"), name
    for w in ("editHmi", "editOut", "editScn", "editScreen", "comboLang", "btnGenerate", "btnOpenResult", "btnOpenFolder",
              "btnBrowseHmi", "btnBrowseOut", "btnBrowseScn", "labelStatus", "textLog"):
        assert w in widgets, w                                       # the object names app.py relies on
    langs = [i.find("property/string").text for i in root.find(".//widget[@name='comboLang']").findall("item")]
    assert langs == ["Magyar", "English"]                            # same order as app.LANGS


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
    win = BuilderWindow(lang="en")
    assert win.w.windowTitle() == "Nextion emulator generator" and win.w.btnGenerate.text() == "▶ Generate"
    win.w.comboLang.setCurrentIndex(0)                               # Magyar
    assert win.w.windowTitle() == "Nextion emulátor generátor" and "Generálás" in win.w.btnGenerate.text()
    win.w.editHmi.setText(str(tmp_path / "w.HMI"))
    assert win.w.editOut.text() == str(tmp_path / "output" / "w")    # output follows the chosen file
    win.generate()
    end = time.time() + 120
    while win.busy and time.time() < end:
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()
    assert (tmp_path / "output" / "w" / "index.html").is_file() and win.w.btnOpenResult.isEnabled()
    assert "coverage: overall" in win.w.textLog.toPlainText()
    win.w.editScreen.setText("bogus")                                # a failed run is reported and nothing can be opened
    win.generate()
    while win.busy and time.time() < end:
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()
    assert "Failed" in win.w.labelStatus.text() or "Hiba" in win.w.labelStatus.text()
    assert not win.w.btnOpenResult.isEnabled()


def test_front_end_and_help_contain_no_project_specific_names(project, tmp_path):
    """Generic assets must not mention names of one particular project; the help takes its examples from the project."""
    banned = re.compile(r"pageMainAuto|charge_level|pageStat|bstart|pageIndividual|bioscale|akku|battery", re.I)
    for f in list((Path(emulator.__file__).parent / "assets").rglob("*")):
        if f.is_file() and f.suffix in (".js", ".html", ".css"):
            assert not banned.search(f.read_text(encoding="utf-8")), f
    for f in Path(emulator.__file__).parents[1].rglob("*.py"):
        if "tests" not in f.parts:
            assert not banned.search(f.read_text(encoding="utf-8")), f
    gen(project, tmp_path)
    help_html = (tmp_path / "help.html").read_text(encoding="utf-8")
    ex = json.loads(re.search(r"const DATA=(.*);", (tmp_path / "data.js").read_text(encoding="utf-8")).group(1))["examples"]
    assert ex["page"] == project.start_page and ex["ref"].endswith(".val") and ex["btn"]
    assert ex["ref"] in help_html and ex["btn"] in help_html                      # examples come from the project


def test_example_picker_has_generic_fallbacks():
    from nextion_parser.emulator.examples import pick_examples
    from nextion_parser.parser import Project
    p = Project.__new__(Project)
    p.pages = []
    assert pick_examples(p, {"start": "p1", "variables": []}) == {
        "page": "p1", "other_page": "p1", "ref": "p1.component.val", "btn": "button", "wave": None}


def test_help_example_json_is_valid(project, tmp_path):
    gen(project, tmp_path)
    for lang_block in re.findall(r'<pre>(\{\s*"name".*?)</pre>', (tmp_path / "help.html").read_text(encoding="utf-8"), re.S):
        scn = json.loads(re.sub(r"&quot;", '"', lang_block).replace("&amp;", "&"))            # the example must be real JSON
        assert scn["steps"] and "{{" not in lang_block
