"""A small document model for the HTML reports, and its renderer.

Reports build a :class:`Doc` from analysis results (cards, headings, tables...) and know nothing about HTML structure or CSS;
:func:`render` turns the model into one self-contained page with a shared light/dark theme. Cell and paragraph contents are
*trusted HTML strings*: build them with :func:`esc`, :func:`code` and :func:`tag` so that data is always escaped.
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass, field

def esc(x) -> str:
    """HTML-escape any value."""
    return _html.escape(str(x))


def code(x) -> str:
    return f"<code>{esc(x)}</code>"


def tag(status: str, text: str | None = None) -> str:
    """A coloured status pill (the class decides the colour, see THEME_CSS)."""
    return f"<span class='tag {esc(status)}'>{esc(text if text is not None else status)}</span>"


# ---------------------------------------------------------------- blocks
@dataclass
class Card:
    title: str
    value: str                       # shown large
    sub: str = ""
    percent: float | None = None     # when given, a coloured progress bar is drawn (>=90 ok, >=60 warn, else bad)


@dataclass
class Cards:
    cards: list[Card]


@dataclass
class Heading:
    text: str
    level: int = 2


@dataclass
class Para:
    html: str
    note: bool = False               # muted colour


@dataclass
class Table:
    headers: list[str]
    rows: list[list[str]]            # cells are trusted HTML
    id: str | None = None
    row_classes: list[str] | None = None


@dataclass
class Details:
    summary: str
    blocks: list = field(default_factory=list)
    open: bool = False


@dataclass
class Bullets:
    items: list[str]                 # trusted HTML


@dataclass
class Pre:
    text: str                        # plain text, escaped on output


@dataclass
class Raw:
    html: str                        # escape hatch (e.g. a script)


@dataclass
class Doc:
    title: str                       # <title> and <h1>
    blocks: list = field(default_factory=list)
    extra_css: str = ""
    lang: str = "en"


THEME_CSS = """
:root{--bg:#f4f5f7;--fg:#1c1f24;--card:#fff;--line:#d5d9e0;--mut:#667085;--ok:#15803d;--warn:#b45309;--bad:#b91c1c;--acc:#1d4ed8}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--fg:#e6e8ec;--card:#1d2026;--line:#333842;--mut:#98a2b3;--ok:#4ade80;--warn:#fbbf24;--bad:#f87171;--acc:#7ea6ff}}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif;max-width:1100px;margin:auto}
h1{font-size:20px}h2{font-size:16px;margin-top:28px}a{color:var(--acc)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
.k{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}.v{font-size:24px;font-weight:600;overflow-wrap:anywhere}.s{color:var(--mut);font-size:12px}
.bar{height:6px;background:var(--line);border-radius:3px;margin:6px 0}.bar i{display:block;height:100%;border-radius:3px}
i.ok{background:var(--ok)}i.warn{background:var(--warn)}i.bad{background:var(--bad)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}th{font-size:12px;color:var(--mut)}
.tag{padding:1px 8px;border-radius:10px;font-size:12px;color:#fff}
.full,.supported,.ok,.used{background:var(--ok)}.partial,.ignored,.redirect,.uncertain,.unresolved-ref{background:var(--warn)}
.unsupported,.unknown,.error,.crash,.bad,.unused,.unreferenced{background:var(--bad)}
code,pre{font:12px ui-monospace,monospace}pre{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;overflow:auto;white-space:pre-wrap}
details{margin:6px 0}summary{cursor:pointer}.note{color:var(--mut)}
"""


# ---------------------------------------------------------------- renderer
def _bar(p: float) -> str:
    cls = "ok" if p >= 90 else "warn" if p >= 60 else "bad"
    return f'<div class="bar"><i class="{cls}" style="width:{p}%"></i></div>'


def _card(c: Card) -> str:
    bar = _bar(c.percent) if c.percent is not None else ""
    return f'<div class="card"><div class="k">{esc(c.title)}</div><div class="v">{esc(c.value)}</div>{bar}<div class="s">{esc(c.sub)}</div></div>'


def _block(b) -> str:
    if isinstance(b, Cards):
        return '<div class="grid">' + "".join(_card(c) for c in b.cards) + "</div>"
    if isinstance(b, Heading):
        return f"<h{b.level}>{esc(b.text)}</h{b.level}>"
    if isinstance(b, Para):
        return f"<p{' class=note' if b.note else ''}>{b.html}</p>"
    if isinstance(b, Table):
        rc = b.row_classes or [None] * len(b.rows)
        rows = "".join(f"<tr{f' class={chr(39)}{c}{chr(39)}' if c else ''}>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>"
                       for r, c in zip(b.rows, rc))
        head = "<tr>" + "".join(f"<th>{esc(h)}</th>" for h in b.headers) + "</tr>"
        return f"<table{f' id={chr(39)}{b.id}{chr(39)}' if b.id else ''}>{head}{rows}</table>"
    if isinstance(b, Details):
        return f"<details{' open' if b.open else ''}><summary>{esc(b.summary)}</summary>" + "".join(_block(x) for x in b.blocks) + "</details>"
    if isinstance(b, Bullets):
        return "<ul>" + "".join(f"<li>{x}</li>" for x in b.items) + "</ul>"
    if isinstance(b, Pre):
        return f"<pre>{esc(b.text)}</pre>"
    if isinstance(b, Raw):
        return b.html
    raise TypeError(f"unknown block: {b!r}")


def render(doc: Doc) -> str:
    body = "".join(_block(b) for b in doc.blocks)
    return (f'<!doctype html><html lang="{esc(doc.lang)}"><meta charset="utf-8"><title>{esc(doc.title)}</title>'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><style>{THEME_CSS}{doc.extra_css}</style>'
            f"<body><h1>{esc(doc.title)}</h1>{body}</body></html>")
