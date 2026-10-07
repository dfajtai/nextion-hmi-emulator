"""Typed description of what the emulator page needs (serialized as ``data.js``).

The emulator generator builds this from a parsed project; the browser code reads it as the global ``DATA``.
Field names follow the JSON keys the page expects (``to_dict`` maps ``csv_profiles`` to ``csvProfiles``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Screen:
    w: int
    h: int
    native: tuple[int, int]


@dataclass
class ReportLink:
    key: str
    href: str


@dataclass
class EmulatorData:
    pages: list[dict]
    picmap: dict[str, str]
    fonts: dict[str, dict]
    screen: Screen
    start: str
    lang: str = "hu"                                   # default GUI language (the user can switch at run time)
    variables: list[dict] = field(default_factory=list)
    csv_profiles: dict = field(default_factory=dict)
    scenarios: list[dict] = field(default_factory=list)
    reports: list[ReportLink] = field(default_factory=list)
    portable: bool = False                             # basic variant: locked to simple mode, no built-in scenarios
    zoom: str | None = None
    examples: dict = field(default_factory=dict)       # real names from the project for placeholders/help examples

    def to_dict(self) -> dict:
        d = {"pages": self.pages, "picmap": self.picmap, "fonts": self.fonts,
             "screen": {"w": self.screen.w, "h": self.screen.h, "native": list(self.screen.native)},
             "start": self.start, "lang": self.lang, "variables": self.variables, "csvProfiles": self.csv_profiles,
             "scenarios": self.scenarios, "examples": self.examples, "reports": [{"key": r.key, "href": r.href} for r in self.reports]}
        if self.portable:
            d["portable"] = True
        if self.zoom:
            d["zoom"] = self.zoom
        return d

    def to_js(self) -> str:
        return "const DATA=" + json.dumps(self.to_dict(), ensure_ascii=False) + ";"
