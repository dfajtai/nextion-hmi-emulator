"""Assembles the emulator page (``index.html``) from its source files in ``assets/ui/``.

Sources (edit these, not the generated page):
  * ``index.html``  - markup shell with the placeholders ``/*__CSS__*/`` and ``/*__JS__*/``
  * ``style.css``   - all styles
  * ``js/NN_name.js`` - the page script split by concern; concatenated in file-name order into ONE classic script
    (they share one scope, and ES modules cannot be loaded from ``file://``)
The result is a single self-contained ``index.html`` (plus the shared ``nextion_core.js`` etc.), so it works offline from disk.
"""
from __future__ import annotations

from importlib import resources

PROJECT_PLACEHOLDER = "__PROJECT__"


def ui_sources():
    return resources.files("nextion_parser.emulator").joinpath("assets", "ui")


def assemble(project_name: str) -> str:
    src = ui_sources()
    css = src.joinpath("style.css").read_text(encoding="utf-8")
    files = sorted((f for f in src.joinpath("js").iterdir() if f.name.endswith(".js")), key=lambda f: f.name)
    js = "".join(f.read_text(encoding="utf-8") for f in files)
    html = src.joinpath("index.html").read_text(encoding="utf-8")
    return html.replace("/*__CSS__*/\n", css).replace("/*__JS__*/\n", js).replace(PROJECT_PLACEHOLDER, project_name)
