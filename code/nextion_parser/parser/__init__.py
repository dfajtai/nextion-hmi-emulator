"""Parser layer: turns an input file into a :class:`~nextion_parser.parser.model.Project`.

This is the replaceable part: ``load`` is the only entry point the rest of the tool uses (see ``ProjectSource``).
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from . import codeutil
from .hmi import load
from .model import PAGE_TYPE, TYPE_NAMES, Component, Font, Image, Page, Project


class ProjectSource(Protocol):
    """Anything that can turn a path into a Project (``load`` of the .HMI reader is one)."""

    def __call__(self, path: str | Path) -> Project: ...


__all__ = ["load", "ProjectSource", "Project", "Page", "Component", "Image", "Font", "TYPE_NAMES", "PAGE_TYPE"]
