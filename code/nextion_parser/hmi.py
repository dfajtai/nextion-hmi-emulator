"""Reader for Nextion .HMI project files.

Format notes (reverse-engineered; see https://github.com/newmatik/nextion-hmi-writer and our own
observations on the sample file):

Container
    u32 section count, then 28-byte directory records:
    ``name[16] | start u32 | size u32 | deleted u8 | 3 bytes``.
    Saving is append-only: a modified section is written as a new copy at the end of the file, the
    old record gets ``deleted=1`` and its first name byte zeroed. Only live (``deleted==0``) records count.
    Payload data starts at offset 0x700000.

Sections (the name encodes the resource number)
    ``N.pa``  page N: 56-byte header (name at 0x18), 12-byte object table, object bodies
    ``N.is``  image N: 27-byte header (0A 64 01, width/height at 0x0C/0x0E) + the original image file
    ``N.i``   editor thumbnail of image N (unused here), ``N.zi`` font N (height at byte 0x07)
    ``Program.s`` start-up code as text, ``main.HMI`` project header + the *order* of the resources
    (a component's ``pic``/``font`` value and the N of a ``page N`` command are the *position in the
    main.HMI resource list*, not the number in the section name).

Object (component)
    ``u32 length + "att-NN"``, then attribute records (``u32 L | name[16] | value[L-16]``),
    then event code (``u32 length + "codes<event>-<lines>"`` + per line ``u32 length + text``).
    Object 0 is the page itself (type 121).
"""
from __future__ import annotations

import re
import struct
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
DIR_REC = 28
_NAME = re.compile(rb"[A-Za-z_][A-Za-z_0-9]*")
_CODES = re.compile(r"codes(\w+?)-(\d+)")
_SECTION = re.compile(r"^(\d+)\.(pa|is|i|zi|ib)$")


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


# ---------------------------------------------------------------- low level
def _u32(d: bytes, o: int) -> int:
    return struct.unpack_from("<I", d, o)[0]


def _parse_object(d: bytes) -> Component | None:
    """Parse one object body (att-NN ... event code)."""
    if len(d) < 8 or d[4:8] != b"att-":
        return None
    p = 4 + len(re.match(rb"att-\d+", d[4:16]).group())
    attrs: dict = {}
    while p + 20 <= len(d):
        n = _u32(d, p)
        if not 16 <= n <= 4000:
            break
        nm = d[p + 4:p + 20].split(b"\0")[0]
        if not _NAME.fullmatch(nm) or nm.startswith(b"codes"):
            break
        raw = d[p + 20:p + 4 + n]
        key = nm.decode()
        attrs[key] = raw.decode("utf8", "replace") if key in STR_ATTRS else \
            int.from_bytes(raw, "little", signed=key in SIGNED_ATTRS)
        p += 4 + n
    if "objname" not in attrs or "type" not in attrs:
        return None
    code: dict[str, list[str]] = {}
    while p + 8 <= len(d):
        n = _u32(d, p)
        if not 4 < n < 40 or d[p + 4:p + 9] != b"codes":
            break
        hm = _CODES.fullmatch(d[p + 4:p + 4 + n].decode("latin1"))
        if not hm:
            break
        p += 4 + n
        lines = []
        for _ in range(int(hm.group(2))):
            ln = _u32(d, p)
            lines.append(d[p + 4:p + 4 + ln].decode("utf8", "replace"))
            p += 4 + ln
        code[hm.group(1)] = lines
    return Component(attrs, code)


def _resource_order(main: bytes) -> dict[str, list[int]]:
    """Resource list of main.HMI: kind (i | zi | pa) -> section numbers in list order."""
    order: dict[str, list[int]] = {"i": [], "zi": [], "pa": []}
    for m in re.finditer(rb"(?<![0-9A-Za-z_.])(\d{1,4})\.(i|zi|pa)\x00", main):
        order[m.group(2).decode()].append(int(m.group(1)))
    return order


def _directory(d: bytes) -> list[dict]:
    n = _u32(d, 0)
    if not 0 < n < 100_000 or 4 + n * DIR_REC > len(d):
        raise ValueError("Not a valid Nextion .HMI file (bad directory)")
    out = []
    for i in range(n):
        o = 4 + i * DIR_REC
        start, size = struct.unpack_from("<II", d, o + 16)
        out.append({"name": d[o:o + 16].split(b"\0")[0].decode("latin1"), "raw0": d[o],
                    "start": start, "size": size, "deleted": d[o + 24]})
    return out


def _parse_page(d: bytes, start: int, size: int, index: int, warnings: list[str]) -> Page | None:
    sec = d[start:start + size]
    if len(sec) < 0x38:
        return None
    info, count = struct.unpack_from("<II", sec, 8)
    name = sec[0x18:0x28].split(b"\0")[0].decode("latin1")
    objs: list[Component] = []
    for i in range(count):
        s, sz, _ = struct.unpack_from("<III", sec, info + 12 * i)
        c = _parse_object(sec[info + s:info + s + sz])
        if c is None:
            warnings.append(f"{index}.pa ({name}): object {i} is not readable")
            continue
        objs.append(c)
    if not objs or objs[0].type != PAGE_TYPE:
        warnings.append(f"{index}.pa ({name}): object 0 is not a page")
        return None
    return Page(index, name, objs[0], objs[1:], count)


_MAGIC = ((b"\x89PNG", "png"), (b"BM", "bmp"), (b"\xff\xd8\xff", "jpg"), (b"GIF8", "gif"))


def _parse_image(d: bytes, start: int, size: int, idx: int, source: str) -> Image | None:
    """``N.is`` / ``N.ib``: 27-byte header (incl. a 3-byte format tag), then the original image file."""
    sec = d[start:start + size]
    if len(sec) < 0x1C or sec[:3] != b"\x0a\x64\x01":
        return None
    w, h = struct.unpack_from("<HH", sec, 0x0C)
    body = sec[0x1B:]
    for magic, ext in _MAGIC:
        if body.startswith(magic):
            return Image(idx, w, h, body, ext, source)
    return None


def _parse_font(d: bytes, start: int, size: int, idx: int) -> Font | None:
    sec = d[start:start + size]
    if len(sec) < 0x30:
        return None
    return Font(idx, sec[7], sec[0x2C:0x4C].split(b"\0")[0].decode("latin1"), sec[5], size)


# ---------------------------------------------------------------- public API
def load(path: str | Path) -> Project:
    path = Path(path)
    d = path.read_bytes()
    warnings: list[str] = []
    ents = _directory(d)
    live = [e for e in ents if not e["deleted"] and e["raw0"] != 0]
    stats = {"total": len(ents), "live": len(live), "deleted": len(ents) - len(live), "other": {}}

    pages: dict[int, Page] = {}
    images: dict[int, Image] = {}
    fonts: dict[int, Font] = {}
    program = ""
    main = b""
    for e in live:
        m = _SECTION.match(e["name"])
        if e["name"] == "main.HMI":
            main = d[e["start"]:e["start"] + e["size"]]
        elif e["name"] == "Program.s":
            program = d[e["start"]:e["start"] + e["size"]].decode("utf8", "replace")
        elif m:
            n, kind = int(m.group(1)), m.group(2)
            if kind == "pa":
                if n in pages:
                    warnings.append(f"{n}.pa appears more than once as a live record")
                pg = _parse_page(d, e["start"], e["size"], n, warnings)
                if pg:
                    pages[n] = pg
            elif kind in ("is", "ib"):
                im = _parse_image(d, e["start"], e["size"], n, kind)
                if im and (kind == "is" or n not in images):
                    images[n] = im        # .is is the instance used on the display, .ib is only a fallback
                elif not im:
                    warnings.append(f"{n}.{kind}: the image is not readable")
            elif kind == "zi":
                f = _parse_font(d, e["start"], e["size"], n)
                if f:
                    fonts[n] = f
            else:                            # .i = editor thumbnail
                stats["other"][kind] = stats["other"].get(kind, 0) + 1
        else:
            stats["other"][e["name"]] = stats["other"].get(e["name"], 0) + 1

    order = _resource_order(main)
    stats["resource_order"] = {k: len(v) for k, v in order.items()}

    def ordered(table: dict, kind: str, what: str) -> dict:
        """Turn a section-number keyed table into a position keyed one, following the main.HMI order."""
        seq = [n for n in order[kind] if n in table]
        missing = [n for n in order[kind] if n not in table]
        extra = sorted(set(table) - set(order[kind]))
        if missing:
            warnings.append(f"main.HMI: {what} listed but missing from the file: {missing}")
        if not order[kind]:                       # no list: fall back to section-number order
            seq = sorted(table)
        elif extra:
            warnings.append(f"{what}: not in the main.HMI list: {extra}")
            seq += extra
        return {i: table[n] for i, n in enumerate(seq)}

    images = {i: Image(i, im.width, im.height, im.data, im.ext, im.source) for i, im in ordered(images, "i", "image").items()}
    fonts = {i: Font(i, f.height, f.name, f.multibyte, f.size_bytes) for i, f in ordered(fonts, "zi", "font").items()}
    plist = []
    for i, pg in ordered(pages, "pa", "page").items():
        pg.index = i
        plist.append(pg)
    for p in plist:
        if p.declared_objects != len(p.comps) + 1:
            warnings.append(f"{p.name}: the header declares {p.declared_objects} objects, "
                            f"{len(p.comps) + 1} are readable")
    start = None
    m = re.search(r"^\s*page\s+(\w+)", program, re.M)
    if m:
        t = m.group(1)
        if t.isdigit():
            start = plist[int(t)].name if int(t) < len(plist) else None      # `page N` = position in the page list
        else:
            start = t
    w = plist[0].page.attrs.get("w", 480) if plist else 480
    h = plist[0].page.attrs.get("h", 272) if plist else 272
    return Project(path, w, h, plist, program, start, images, fonts, stats, warnings)
