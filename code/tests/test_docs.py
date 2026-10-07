"""The documentation: every relative link in the README and the docs must point to an existing file."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = [ROOT / "README.md", ROOT / "sample" / "README.md", *sorted((ROOT / "docs").glob("*.md"))]


def test_docs_are_numbered_and_linked_from_the_readme():
    names = [p.name for p in (ROOT / "docs").glob("*.md")]
    assert names and all(re.match(r"\d\d_", n) for n in names)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert all(f"docs/{n}" in readme for n in names), "every docs page is listed in the README table of contents"
    assert len(readme.splitlines()) < 80, "the README stays a short entry point; details go into docs/"


def test_relative_links_resolve():
    broken = []
    for page in PAGES:
        for m in re.finditer(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", page.read_text(encoding="utf-8")):
            target = m.group(1)
            if not target.startswith(("http://", "https://", "mailto:")) and not (page.parent / target).exists():
                broken.append((page.name, target))
    assert not broken, broken
