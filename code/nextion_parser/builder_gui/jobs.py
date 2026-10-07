"""Runs a generation in the same way as the command line, collecting the log. No GUI imports here."""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .. import cli


@dataclass
class JobResult:
    rc: int
    log: str
    launcher: Path | None = None
    errors: list[str] = field(default_factory=list)


class _Tee(io.TextIOBase):
    """Collects everything written and forwards it line-wise to a callback (used to stream the log into the window)."""

    def __init__(self, emit: Callable[[str], None] | None):
        self.parts: list[str] = []
        self.emit = emit

    def write(self, s: str) -> int:
        self.parts.append(s)
        if self.emit and s:
            self.emit(s)
        return len(s)


def default_output(hmi: Path) -> Path:
    return hmi.parent / "output" / hmi.stem


def build_args(hmi: Path, out: Path | None = None, lang: str = "hu", screen: str = "", scenarios: str = "") -> list[str]:
    args = ["all", str(hmi), "-o", str(out or default_output(hmi)), "--lang", lang]
    if screen.strip():
        args += ["--screen", screen.strip()]
    if scenarios.strip():
        args += ["--scenarios", scenarios.strip()]
    return args


def run_generation(hmi: str | Path, out: str | Path | None = None, lang: str = "hu", screen: str = "", scenarios: str = "",
                   emit: Callable[[str], None] | None = None) -> JobResult:
    """Generate everything for one HMI file (the equivalent of ``nextion_parser all ...``)."""
    hmi = Path(hmi)
    if not hmi.is_file():
        return JobResult(2, "", None, [f"not a file: {hmi}"])
    out = Path(out) if out else default_output(hmi)
    out_t, err_t = _Tee(emit), _Tee(emit)
    try:
        with contextlib.redirect_stdout(out_t), contextlib.redirect_stderr(err_t):
            rc = cli.main(build_args(hmi, out, lang, screen, scenarios))
    except SystemExit as e:                    # argparse errors (e.g. a malformed --screen) end up here
        rc = int(e.code or 1)
    except Exception as e:                     # never let a worker thread die silently
        err_t.write(f"Error: {e}\n")
        rc = 1
    launcher = out / "index.html"
    ok = rc in (0, 4) and launcher.is_file()               # 4 = generated, but some scenarios do not match the HMI
    return JobResult(rc, "".join(out_t.parts) + "".join(err_t.parts), launcher if ok else None,
                     "".join(err_t.parts).strip().splitlines())
