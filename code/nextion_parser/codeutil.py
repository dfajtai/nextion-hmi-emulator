"""Shared helpers for line-by-line processing of Nextion code."""
from __future__ import annotations


def statements(lines: list[str]):
    for raw in lines:
        s, q, out = raw, False, ""
        for i, ch in enumerate(s):
            if ch == '"':
                q = not q
            if not q and ch == "/" and s[i + 1:i + 2] == "/":
                break
            out += ch
        s = out.strip()
        while s.startswith("}") and len(s) > 1:
            s = s[1:].strip()
        if s.endswith("{") and len(s) > 1:
            s = s[:-1].strip()
        if s in ("", "{", "}"):
            continue
        yield s
