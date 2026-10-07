"""Command line, launcher page, exit codes and the single-file easy generator."""
from pathlib import Path
import shutil
import subprocess

from nextion_parser import emulator
from nextion_parser.cli import main

from helpers import SAMPLE, SCN, needs_sample

pytestmark = needs_sample


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


def test_all_writes_launcher_and_portable(tmp_path):
    out = tmp_path / "o"
    assert main(["all", str(SAMPLE), "-o", str(out), "--scenarios", str(SCN)]) == 0
    idx = (out / "index.html").read_text(encoding="utf-8")
    for href in ("emulator/index.html", "portable/index.html", "coverage/coverage.html"):
        assert href in idx
    assert (out / "portable" / "serve.py").is_file() and (out / "portable" / "start.bat").is_file() and (out / "portable" / "update_scenarios.py").is_file()
    assert (out / "scripts" / "update_scenarios.py").is_file() and (out / "portable" / "scenarios").is_dir() and not (out / "scenarios").exists()
    assert (out / "emulator" / "scenarios.js").is_file() and (out / "portable" / "scenarios.js").is_file()


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
