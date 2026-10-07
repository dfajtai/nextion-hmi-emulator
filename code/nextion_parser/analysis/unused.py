"""Report of unused (unreferenced) resources, to help "compressing" the HMI.

The file is not modified (writing .HMI files is not supported); the report tells you what is worth deleting in the
Nextion Editor. The ids are the Editor's: image and font ids are positions in the main.HMI resource list.

What counts as a reference:
  * component attribute: ``pic``, ``pic2`` (image), ``font`` (font) - and the ``pic`` background of a page
  * code: literal assignments ``obj.pic=N``, ``obj.pic2=N``, ``obj.font=N``; the commands ``pic x,y,N`` /
    ``picq x,y,w,h,N`` / ``xpic dx,dy,w,h,sx,sy,N``; the font parameter of ``xstr``/``spstr``
  * a non-literal assignment (e.g. ``pbattery.pic=pic_index.val``) is *uncertain*: the images are then not
    necessarily unused
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from ..parser import Project, codeutil
from ..parser.hmi import section_sizes

_ASSIGN = re.compile(r"^([A-Za-z_][\w\.]*)\.(pic|pic2|bpic|ppic|font)\s*=\s*(.+)$")
NONE = 0xFFFF


def _lit(expr: str) -> int | None:
    expr = expr.strip()
    return int(expr) if re.fullmatch(r"\d+", expr) else None


def _split(s: str) -> list[str]:
    out, d, cur = [], 0, ""
    for ch in s:
        if ch in "([":
            d += 1
        elif ch in ")]":
            d -= 1
        if ch == "," and d == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return out


def _scan(project: Project) -> dict:
    img: dict[int, list[str]] = defaultdict(list)
    fnt: dict[int, list[str]] = defaultdict(list)
    dyn_img: list[str] = []
    dyn_font: list[str] = []
    page_targets: dict[str, list[str]] = defaultdict(list)
    names = {p.name for p in project.pages}
    for p in project.pages:
        for c in [p.page] + p.comps:
            for k in ("pic", "pic2", "bpic", "ppic"):
                v = c.attrs.get(k)
                if v is not None and v != NONE and c.type != 52:
                    img[v].append(f"{p.name}.{c.name}.{k}" if c.type != 121 else f"{p.name} (page background)")
            if "font" in c.attrs and c.type in (54, 59, 98, 116):
                fnt[c.attrs["font"]].append(f"{p.name}.{c.name}")
        for cname, code in [("(page)", p.code)] + [(c.name, c.code) for c in p.comps]:
            for ev, lines in code.items():
                where = f"{p.name}.{cname}.{ev}"
                for s in codeutil.statements(lines):
                    m = _ASSIGN.match(s)
                    if m:
                        n = _lit(m.group(3))
                        target = f"{where} → {m.group(1)}.{m.group(2)}"
                        if m.group(2) == "font":
                            (fnt[n].append(target) if n is not None else dyn_font.append(target))
                        else:
                            (img[n].append(target) if n is not None else dyn_img.append(f"{target}={m.group(3)}"))
                    m = re.match(r"^(pic|picq|xpic)\s+(.*)$", s)
                    if m:
                        a = _split(m.group(2))
                        n = _lit(a[-1])
                        (img[n].append(f"{where} → {m.group(1)}") if n is not None else dyn_img.append(f"{where} → {m.group(1)} {m.group(2)}"))
                    m = re.match(r"^(xstr|spstr)\s+(.*)$", s)
                    if m:
                        a = _split(m.group(2))
                        n = _lit(a[4]) if m.group(1) == "xstr" and len(a) > 4 else None
                        if n is not None:
                            fnt[n].append(f"{where} → xstr")
                    m = re.match(r"^page\s+(.+)$", s)
                    if m:
                        t = m.group(1).strip()
                        if t in names:
                            page_targets[t].append(where)
                        elif t.isdigit() and int(t) < len(project.pages):
                            page_targets[project.pages[int(t)].name].append(where)
                        else:
                            page_targets["*dynamic*"].append(where)
    return {"img": img, "font": fnt, "dyn_img": dyn_img, "dyn_font": dyn_font, "pages": page_targets}


def _component_usage(project: Project) -> list[dict]:
    """Non-visual components (timer, variable, hotspot) that nothing refers to."""
    text = defaultdict(str)
    for p in project.pages:
        for code in [p.code] + [c.code for c in p.comps]:
            for lines in code.values():
                text[p.name] += "\n".join(lines) + "\n"
    all_text = "\n".join(text.values())
    out = []
    for p in project.pages:
        for c in p.comps:
            if c.type not in (51, 52, 109, 113):
                continue
            has_code = any(c.code.values())
            name = re.escape(c.name)
            local = re.search(rf"(?<![\w.]){name}(?![\w])", text[p.name]) is not None
            glob = re.search(rf"\b{re.escape(p.name)}\.{name}\b", all_text) is not None
            referenced = local or glob
            if c.type == 109 and has_code:
                continue
            if c.type == 51 and has_code:
                continue                                 # useful because of its timer code
            if not referenced and not has_code:
                out.append({"page": p.name, "name": c.name, "type": c.type_name,
                            "scope": "global" if c.attrs.get("vscope") == 1 else "local",
                            "note": ("global: the MCU may use it" if c.attrs.get("vscope") == 1 else "local and nothing refers to it")})
    return out


def analyze(project: Project) -> dict:
    scan = _scan(project)
    sizes = section_sizes(project.path)
    uncertain_img = bool(scan["dyn_img"])
    uncertain_font = bool(scan["dyn_font"])

    images = []
    for i, im in sorted(project.images.items()):
        refs = scan["img"].get(i, [])
        images.append({"id": i, "width": im.width, "height": im.height, "format": im.ext, "refs": refs,
                       "tft_bytes": im.width * im.height * 2,
                       "status": "used" if refs else ("uncertain" if uncertain_img else "unused")})
    fonts = []
    for i, f in sorted(project.fonts.items()):
        refs = scan["font"].get(i, [])
        fonts.append({"id": i, "name": f.name, "height": f.height, "refs": refs, "bytes": f.size_bytes,
                      "status": "used" if refs else ("uncertain" if uncertain_font else "unused")})
    start = project.start_page
    pages = []
    for p in project.pages:
        t = scan["pages"].get(p.name, [])
        status = "used" if t or p.name == start else ("uncertain" if scan["pages"].get("*dynamic*") else "unreferenced")
        pages.append({"index": p.index, "name": p.name, "referenced_from": t[:5], "components": len(p.comps),
                      "status": status,
                      "note": "" if status == "used" else "no `page` reference in the HMI code; the MCU may still reach it with a serial `page` command"})
    comps = _component_usage(project)
    unused_img = [x for x in images if x["status"] == "unused"]
    unused_fnt = [x for x in fonts if x["status"] == "unused"]
    summary = {
        "images_total": len(images), "images_unused": len(unused_img),
        "images_unused_tft_bytes": sum(x["tft_bytes"] for x in unused_img),
        "images_tft_bytes": sum(x["tft_bytes"] for x in images),
        "fonts_total": len(fonts), "fonts_unused": len(unused_fnt), "fonts_unused_bytes": sum(x["bytes"] for x in unused_fnt),
        "pages_unreferenced": sum(1 for x in pages if x["status"] == "unreferenced"),
        "pages_uncertain": sum(1 for x in pages if x["status"] == "uncertain"),
        "components_unused": len(comps),
        "hmi_file_bytes": sizes["file_bytes"], "hmi_dead_bytes": sizes["dead_bytes"],
        "dynamic_image_refs": len(scan["dyn_img"]), "dynamic_font_refs": len(scan["dyn_font"]),
    }
    return {"project": project.name, "summary": summary, "images": images, "fonts": fonts, "pages": pages,
            "components": comps, "dynamic": {"images": scan["dyn_img"], "fonts": scan["dyn_font"]}}
