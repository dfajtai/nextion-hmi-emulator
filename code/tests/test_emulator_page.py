"""The emulator page (generated HTML/JS), its core interpreter, dictionaries and help."""
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from nextion_parser import emulator

from helpers import DATA_DIR, SCN, TEMPLATES, gen, needs_node, needs_sample, script_of

pytestmark = needs_sample


def test_emulator_embeds_scenarios(project, tmp_path):
    gen(project, tmp_path)
    data = (tmp_path / "data.js").read_text(encoding="utf-8")
    assert '"scenarios"' in data and '"variables"' in data and '"csvProfiles"' in data and "pageStat1.xmean.val" in data


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


def test_emulator_has_server_sync(project, tmp_path):
    html = gen(project, tmp_path)
    assert "api/scenarios" in html and "syncServer" in html and "rec.info.saved.server" in html


def test_restart_resets_the_scenario_too(project, tmp_path):
    html = gen(project, tmp_path)
    handler = re.search(r"\$\('reset'\)\.onclick=\(\)=>\{(.*?)\n\};", html, re.S).group(1)
    assert "stopScn()" in handler and "boot()" in handler and "play.scn&&!rec.on" in handler


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


def test_help_example_json_is_valid(project, tmp_path):
    gen(project, tmp_path)
    for lang_block in re.findall(r'<pre>(\{\s*"name".*?)</pre>', (tmp_path / "help.html").read_text(encoding="utf-8"), re.S):
        scn = json.loads(re.sub(r"&quot;", '"', lang_block).replace("&amp;", "&"))            # the example must be real JSON
        assert scn["steps"] and "{{" not in lang_block


def test_screenshot_button_and_embedded_images(project, tmp_path):
    html = gen(project, tmp_path)
    assert 'id="shot"' in html and "saveScreenshot" in html and "showSaveFilePicker" in html
    assert '<script src="images.js"></script>' in html
    assert 'id="shotcopy"' in html and "copyScreenshot" in html and "new ClipboardItem" in html     # clipboard variant
    btn = re.search(r'<button id="shot"[^>]*>', html).group(0)
    assert "expert" not in btn                                       # available in the simple/basic mode too
    imgs = (tmp_path / "images.js").read_text(encoding="utf-8")
    assert imgs.startswith("window.NX_IMG=") and '"img/0.png":"data:image/png;base64,' in imgs
    assert len(json.loads(imgs[len("window.NX_IMG="):].rstrip(";\n"))) == len(project.images)


def test_screenshot_renders_a_png_in_headless_chrome(project, tmp_path):
    """End to end from file:// (the hard case: pictures must be embedded): the display is drawn into a native-size PNG."""
    import base64
    import struct
    chrome = next((shutil.which(c) for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if shutil.which(c)), None)
    if not chrome:
        pytest.skip("no Chrome/Chromium for the headless screenshot test")
    gen(project, tmp_path)
    page = tmp_path / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace("</body>", """<script>addEventListener('load',()=>setTimeout(async()=>{
      try{const b=await shotCanvas();const f=new FileReader();f.onload=()=>{document.body.setAttribute('data-shot',f.result);document.title='DONE'};f.readAsDataURL(b);}
      catch(e){document.title='ERR '+e.message}},1500));</script></body>""", 1), encoding="utf-8")
    r = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=12000", "--dump-dom",
                        page.as_uri() + "?lang=en"], capture_output=True, text=True, timeout=90)
    m = re.search(r'data-shot="data:image/png;base64,([^"]+)"', r.stdout)
    assert m, re.search(r"<title>([^<]*)", r.stdout)
    png = base64.b64decode(m.group(1))
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", png[16:24])
    assert (w, h) == (project.width, project.height)                  # native display resolution
