"""Data model of a parsed Nextion project (the contract between a parser and everything that consumes a project).

A different parser (another file format, a live device, a JSON dump...) only has to produce a :class:`Project`;
analyses, reports and the emulator generator depend on this module, never on the .HMI reader.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PAGE_TYPE = 121
STR_ATTRS = {"txt", "objname"}
SIGNED_ATTRS = {"val", "minval", "maxval"}
TYPE_NAMES = {
    0: "waveform", 1: "slider", 51: "timer", 52: "variable", 53: "dataRecord",
    54: "number", 55: "progressBar", 56: "checkbox", 57: "radio", 59: "xfloat",
    98: "button", 106: "progressBar", 109: "hotspot", 112: "picture", 113: "crop",
    116: "text", 121: "page",
}


@dataclass
class Component:
    attrs: dict
    code: dict

    @property
    def name(self) -> str:
        return self.attrs.get("objname", "")

    @property
    def type(self) -> int:
        return self.attrs.get("type", -1)

    @property
    def id(self) -> int:
        return self.attrs.get("id", -1)

    @property
    def type_name(self) -> str:
        return TYPE_NAMES.get(self.type, f"type{self.type}")

    def to_dict(self) -> dict:
        d = dict(self.attrs)
        d["code"] = dict(self.code)
        return d


@dataclass
class Page:
    index: int                 # position in the main.HMI page list (what the `page N` command uses)
    name: str
    page: Component
    comps: list[Component] = field(default_factory=list)
    declared_objects: int = 0  # object count according to the header (the page itself included)

    @property
    def code(self) -> dict:
        return self.page.code


@dataclass
class Image:
    id: int
    width: int
    height: int
    data: bytes = field(repr=False)
    ext: str = "png"          # format of the embedded original file (png/bmp/jpg/gif)
    source: str = "is"        # which section it came from (is | ib)


@dataclass
class Font:
    id: int
    height: int
    name: str
    multibyte: int
    size_bytes: int = 0


@dataclass
class Project:
    path: Path
    width: int
    height: int
    pages: list[Page]
    program: str
    start_page: str | None
    images: dict[int, Image]
    fonts: dict[int, Font]
    sections: dict                    # directory statistics
    warnings: list[str]

    @property
    def name(self) -> str:
        return self.path.stem

    def page(self, name: str) -> Page | None:
        return next((p for p in self.pages if p.name == name), None)
