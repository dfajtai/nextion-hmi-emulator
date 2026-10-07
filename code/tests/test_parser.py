"""Reading the .HMI file."""

import pytest

from nextion_parser import emulator, parser
from nextion_parser.analysis import coverage as cov_a
from nextion_parser.analysis import navigation

from helpers import SAMPLE_OLD, needs_sample

pytestmark = needs_sample


def test_directory_and_pages(project):
    names = {p.name for p in project.pages}
    assert {"pageMainAuto", "pageMenu", "pageCal"} <= names
    assert project.pages[0].name == "pageMainAuto" and project.start_page == "pageMainAuto"
    assert (project.width, project.height) == (480, 272)
    assert project.sections["live"] + project.sections["deleted"] == project.sections["total"]
    assert not project.warnings                          # object counts match the page headers


def test_images_follow_resource_order(project):
    # the pic id is the position in the main.HMI resource list; the sizes confirm it (>95 % match)
    rs = cov_a.static_resources(project)
    assert rs["image_dim_percent"] > 95
    assert not rs["images_missing"] and not rs["fonts_missing"]
    assert all(im.data[:4] == b"\x89PNG" for im in project.images.values())


def test_navigation_edge(project):
    edges, _ = navigation.navigation(project)
    assert "bcalibration.down" in edges[("pageMenu", "pageCal")]


def test_program(project):
    assert "int sys0" in project.program


def test_invalid_file_is_rejected(tmp_path):
    bad = tmp_path / "bad.HMI"
    bad.write_bytes(b"\x00" * 64)
    with pytest.raises(ValueError, match="Not a valid"):
        parser.load(bad)


@pytest.mark.skipif(not SAMPLE_OLD.exists(), reason="the older sample (Editor 1.6.8.1) is not present")
def test_editor_1_6_8_1_and_1_6_8_2_files_are_read_identically(project):
    """The same project saved by Editor 1.6.8.1 (old) and 1.6.8.2 (the committed sample) gives the same model;
    only the deleted ('dead') sections differ."""
    old = parser.load(SAMPLE_OLD)
    assert (old.width, old.height, old.start_page) == (project.width, project.height, project.start_page)
    assert [p.name for p in old.pages] == [p.name for p in project.pages]
    for a, b in zip(old.pages, project.pages):
        assert a.page.attrs == b.page.attrs and a.code == b.code
        assert [(c.attrs, c.code) for c in a.comps] == [(c.attrs, c.code) for c in b.comps]
    assert {i: im.data for i, im in old.images.items()} == {i: im.data for i, im in project.images.items()}
    assert old.program == project.program and not old.warnings and not project.warnings
    assert emulator.build_data(old)["pages"] == emulator.build_data(project)["pages"]
