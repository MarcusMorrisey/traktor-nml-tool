"""Guards the vendored IBM Plex faces: the files themselves, and the
mount that serves them.

Reads bytes and source text, never a font-family name. `theme.FONT_SANS`
named IBM Plex for the whole period the served page painted Segoe UI, so
a guard asserting that name is true in exactly the broken state
(DL-165). These guards run under the system interpreter, which has no
nicegui, so nothing here imports `traktor_nml.gui.app` (DL-178).
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

import pytest

from traktor_nml.gui import theme

REPO_ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = REPO_ROOT / "traktor_nml" / "gui" / "fonts"
APP_PATH = REPO_ROOT / "traktor_nml" / "gui" / "app.py"
GUI_README = REPO_ROOT / "traktor_nml" / "gui" / "README.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"
SPEC = REPO_ROOT / "traktor-nml-spike.spec"

# Each face as vendored: file name -> (bytes, sha256). Held here and in
# traktor_nml/gui/README.md's table; the guard below checks the two
# agree, so neither can drift from the files alone.
VENDORED = {
    "IBMPlexSans-Regular.woff2": (63020, "ba711a3085ff9f27440b6b9c4550cfc47c97bf36591d5da958b975bb3add8c1a"),
    "IBMPlexSans-Medium.woff2": (66740, "5660f8a658f8bb50dbc005232f885eadffd2bc1c235c4f6fbb63469d1f9cde6d"),
    "IBMPlexSans-SemiBold.woff2": (67060, "f78048030eab62e860efa39a0df79e2e5581bf122eb95b9bc42c0b8a4988d205"),
    "IBMPlexSans-Bold.woff2": (63012, "fa7130d854a660b39a7fc9e6e0f2dc23dba5f1346e2adea3e1fe37b6d884133d"),
    "IBMPlexMono-Regular.woff2": (45640, "49ce58b41a0e1cb921c0f58d9a5b8b96a2cc21437c7066f3ba4f24873076d131"),
    "IBMPlexMono-Medium.woff2": (46724, "8c2c290cbd998fa1f647e4572aca6ebbd72589551b0f3f9f8bb8628fbb8219d5"),
    "IBMPlexMono-SemiBold.woff2": (47016, "ed5eaca7522336959d6c3810bd9bb78424f0d964082d581bfbea169ee08d14e3"),
}

MEASURED_TOTAL = 399212


@pytest.mark.parametrize("file_name", sorted(VENDORED), ids=str)
def test_each_vendored_face_matches_its_recorded_size_and_hash(file_name: str):
    """Each face is present and is the exact upstream file recorded in
    traktor_nml/gui/README.md - byte length and SHA-256 both.

    Mutation: one byte of IBMPlexMono-Regular.woff2 was flipped and
    this guard rerun. Observed:
        AssertionError: IBMPlexMono-Regular.woff2 hashes to
        fce1f115... , not the recorded 49ce58b4...
    """
    path = FONTS_DIR / file_name
    assert path.is_file(), f"{file_name} is absent from traktor_nml/gui/fonts/"
    data = path.read_bytes()
    size, digest = VENDORED[file_name]
    assert len(data) == size, f"{file_name} is {len(data)} bytes, not the recorded {size}"
    actual = hashlib.sha256(data).hexdigest()
    assert actual == digest, (
        f"{file_name} hashes to {actual[:8]}... , not the recorded {digest[:8]}..."
    )


def test_each_face_is_a_woff2_file():
    """Every vendored face carries the wOF2 magic number, so a file
    renamed to .woff2 from another format is caught here rather than by
    a browser refusing it silently at run time.

    Mutation: IBMPlexSans-Bold.woff2 was replaced by a copy of OFL.txt
    and this guard rerun. Observed:
        AssertionError: files whose first four bytes are not wOF2:
        ['IBMPlexSans-Bold.woff2']
        assert ['IBMPlexSans-Bold.woff2'] == []
    """
    wrong = sorted(
        name
        for name in VENDORED
        if (FONTS_DIR / name).read_bytes()[:4] != b"wOF2"
    )
    assert wrong == [], f"files whose first four bytes are not wOF2: {wrong}"


def test_the_directory_holds_the_measured_total_and_nothing_else():
    """The directory holds exactly the seven declared faces, and their
    bytes sum to the total traktor_nml/gui/README.md records. An eighth
    face, or a face swapped for a larger one, fails here rather than
    passing under a ceiling with room in it (DL-176).

    Mutation: IBMPlexSans-Regular.woff2 was copied to
    IBMPlexSans-Thin.woff2 and this guard rerun. Observed:
        AssertionError: traktor_nml/gui/fonts/ holds faces that
        FONT_FACES does not declare: ['IBMPlexSans-Thin.woff2']
        assert ['IBMPlexSans-Thin.woff2'] == []
    """
    present = {path.name for path in FONTS_DIR.glob("*.woff2")}
    undeclared = sorted(present - set(VENDORED))
    assert undeclared == [], (
        f"traktor_nml/gui/fonts/ holds faces that FONT_FACES does not declare: {undeclared}"
    )
    total = sum((FONTS_DIR / name).stat().st_size for name in present)
    assert total == MEASURED_TOTAL, (
        f"the vendored faces total {total} bytes, not the recorded {MEASURED_TOTAL}"
    )


def test_the_licence_ships_beside_the_faces():
    """OFL.txt is present and is the SIL Open Font License 1.1 the
    faces are licensed under (DL-166).

    Mutation: OFL.txt was renamed to LICENSE.txt and this guard rerun.
    Observed:
        AssertionError: traktor_nml/gui/fonts/OFL.txt is absent
        assert False
    """
    licence = FONTS_DIR / "OFL.txt"
    assert licence.is_file(), "traktor_nml/gui/fonts/OFL.txt is absent"
    text = licence.read_text(encoding="utf-8")
    assert "SIL Open Font License, Version 1.1" in text


def test_the_readme_table_records_every_face_with_its_size_and_hash():
    """traktor_nml/gui/README.md's table and VENDORED above hold the
    same size and hash for every face, so the prose record and the
    guard cannot drift apart.

    Mutation: the IBMPlexMono-Medium row's byte count in the README
    table was changed from 46724 to 46725 and this guard rerun.
    Observed:
        AssertionError: README and VENDORED disagree on
        IBMPlexMono-Medium.woff2: README says (46725, '8c2c290c'),
        the guard says (46724, '8c2c290c')
    """
    text = GUI_README.read_text(encoding="utf-8")
    rows = dict(
        (name, (int(size), digest))
        for name, size, digest in re.findall(
            r"\|\s*`([A-Za-z0-9-]+\.woff2)`\s*\|[^|]*\|\s*(\d+)\s*\|\s*`([0-9a-f]{64})`\s*\|",
            text,
        )
    )
    assert set(rows) == set(VENDORED), (
        f"README table names {sorted(set(rows) ^ set(VENDORED))} differently from the guard"
    )
    for name, recorded in rows.items():
        assert recorded == VENDORED[name], (
            f"README and VENDORED disagree on {name}: README says "
            f"({recorded[0]}, '{recorded[1][:8]}'), the guard says "
            f"({VENDORED[name][0]}, '{VENDORED[name][1][:8]}')"
        )
    assert str(MEASURED_TOTAL) in text, (
        f"README does not state the measured total {MEASURED_TOTAL}"
    )


def test_app_py_mounts_the_directory_at_the_constant_theme_names():
    """app.py's add_static_files call passes theme.FONT_URL_BASE as its
    route rather than a path literal of its own, so the @font-face src
    and the route that answers it cannot diverge (DL-164). Read by
    walking app.py's AST, because the system interpreter has no nicegui
    and cannot import the module.

    Mutation: the call's first argument was replaced with the literal
    "/static/fonts" and this guard rerun. Observed:
        AssertionError: add_static_files is passed Constant, not
        theme.FONT_URL_BASE
    """
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_static_files"
    ]
    assert len(calls) == 1, f"app.py makes {len(calls)} add_static_files calls, not one"
    route = calls[0].args[0]
    assert isinstance(route, ast.Attribute) and route.attr == "FONT_URL_BASE", (
        f"add_static_files is passed {type(route).__name__}, not theme.FONT_URL_BASE"
    )
    assert isinstance(route.value, ast.Name) and route.value.id == "theme"


def test_the_fonts_directory_reaches_the_wheel_and_the_frozen_build():
    """pyproject.toml carries the faces as package data and the
    PyInstaller spec carries the directory in datas. Without both, a
    built artefact answers 404 for every face and falls back silently -
    the same silence, reached by a different route (DL-168).

    Mutation: the [tool.setuptools.package-data] block was deleted from
    pyproject.toml and this guard rerun. Observed:
        assert '[tool.setuptools.package-data]' in
        '[build-system]
requires = ["setuptools>=61.0"]
...'
    """
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    assert "[tool.setuptools.package-data]" in pyproject
    assert "fonts/*.woff2" in pyproject, (
        "pyproject.toml does not carry the faces as package data"
    )
    assert "fonts/OFL.txt" in pyproject
    spec = SPEC.read_text(encoding="utf-8")
    assert "traktor_nml/gui/fonts" in spec, (
        "traktor-nml-spike.spec does not carry the fonts directory in datas"
    )
