"""Shared test helpers: sample paths, markers and the generator helper."""
import re
import shutil
from pathlib import Path

import pytest

from nextion_parser import emulator

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample"
SAMPLE = SAMPLE_DIR / "bioscale_research_new.HMI"          # committed sample, saved by Nextion Editor 1.6.8.2
SAMPLE_OLD = SAMPLE_DIR / "bioscale_research_old.HMI"      # the same project saved by 1.6.8.1 (optional, git-ignored)
SCN = Path(__file__).parent / "fixtures" / "scenarios"
DATA_DIR = SAMPLE_DIR / "data"
TEMPLATES = Path(emulator.__file__).parent / "assets"
needs_sample = pytest.mark.skipif(not SAMPLE.exists(), reason="no sample HMI")
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")


def gen(project, tmp_path, **kw):
    """Generate the emulator for `project` into tmp_path and return its index.html text."""
    emulator.generate(project, tmp_path, scenario_dir=SCN, **kw)
    return (tmp_path / "index.html").read_text(encoding="utf-8")


def script_of(html: str) -> str:
    return re.findall(r"<script>(.*?)</script>", html, re.S)[-1]
