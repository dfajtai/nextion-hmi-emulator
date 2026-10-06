"""Tiny helper for localized fields in scenario / variable files.

A localized field is either a plain string or a mapping ``{"hu": "...", "en": "..."}``.
"""
from __future__ import annotations

FALLBACK = ("en", "hu")


def loc(value, lang: str = "en") -> str:
    """Return the text of a (possibly localized) field in ``lang``, falling back to en / hu / any value."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for k in (lang, *FALLBACK):
            if isinstance(value.get(k), str) and value[k]:
                return value[k]
        for v in value.values():
            if isinstance(v, str) and v:
                return v
        return ""
    return str(value)
