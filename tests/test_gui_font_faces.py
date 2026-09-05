"""Guards the @font-face blocks theme.py emits.

Asserts the literal seven (DL-179): a guard that only checks each
declared face is emitted stays green when a weight is dropped from
FONT_FACES, because the tuple it iterates got shorter too. The count is
what a dropped weight changes.
"""

from __future__ import annotations

import re

from traktor_nml.gui import theme

# The weights design/reconnect-wizard/Main.dc.html line 11 imports.
ARTBOARD_FACES = {
    ("IBM Plex Sans", 400),
    ("IBM Plex Sans", 500),
    ("IBM Plex Sans", 600),
    ("IBM Plex Sans", 700),
    ("IBM Plex Mono", 400),
    ("IBM Plex Mono", 500),
    ("IBM Plex Mono", 600),
}

_FACE_BLOCK = re.compile(
    r"@font-face \{[^}]*font-family: '([^']+)'[^}]*font-weight: (\d+)[^}]*"
    r"src: url\('([^']+)'\) format\('woff2'\)[^}]*\}"
)


def test_font_faces_declares_exactly_the_weights_the_artboard_imports():
    """FONT_FACES holds seven entries and they are the seven the
    artboard imports - no extra weight, none missing.

    Mutation: the ("IBM Plex Mono", 500, ...) entry was deleted from
    FONT_FACES and this guard rerun. Observed:
        AssertionError: FONT_FACES declares 6 faces, not 7
        assert 6 == 7
    """
    assert len(theme.FONT_FACES) == 7, (
        f"FONT_FACES declares {len(theme.FONT_FACES)} faces, not 7"
    )
    declared = {(family, weight) for family, weight, _ in theme.FONT_FACES}
    assert declared == ARTBOARD_FACES


def test_the_stylesheet_emits_one_block_per_declared_face():
    """The emitted sheet holds exactly seven @font-face blocks, and
    each parses to a family, a weight and a woff2 src. The count is
    asserted against the literal seven rather than against
    len(FONT_FACES), which a dropped weight changes in step.

    Mutation: font_face_rules() was changed to iterate
    FONT_FACES[:-1] and this guard rerun. Observed:
        AssertionError: the stylesheet emits 6 @font-face blocks, not 7
        assert 6 == 7
    """
    sheet = theme.page_stylesheet()
    blocks = _FACE_BLOCK.findall(sheet)
    assert len(blocks) == 7, (
        f"the stylesheet emits {len(blocks)} @font-face blocks, not 7"
    )
    emitted = {(family, int(weight)) for family, weight, _ in blocks}
    assert emitted == ARTBOARD_FACES


def test_every_src_names_the_mount_route_and_a_declared_file():
    """Each block's src is FONT_URL_BASE joined to the file name that
    entry declares, so a block cannot name a file the directory does
    not hold or a route the mount does not answer.

    Mutation: FONT_URL_BASE was changed to "/static/fonts" while
    app.py's mount was left reading the old value; this guard was
    rerun against a copy of FONT_FACES holding the old paths. Observed:
        AssertionError: src '/static/fonts/IBMPlexSans-Regular.woff2'
        is not FONT_URL_BASE joined to a declared file
    """
    sheet = theme.page_stylesheet()
    expected = {
        f"{theme.FONT_URL_BASE}/{file_name}"
        for _, _, file_name in theme.FONT_FACES
    }
    for _family, _weight, src in _FACE_BLOCK.findall(sheet):
        assert src in expected, (
            f"src {src!r} is not FONT_URL_BASE joined to a declared file"
        )


def test_the_face_blocks_precede_the_body_rule_that_names_the_family():
    """The @font-face blocks are emitted above the body rule naming
    FONT_SANS, and unlayered, which places them after Quasar's own
    layered Roboto default in the cascade (DL-173). A block emitted
    inside the quasar_importants layer would lose to it.

    Mutation: the {font_face_rules()} interpolation was moved below the
    body rule and this guard rerun. Observed:
        AssertionError: the body rule at offset 329 precedes the
        first @font-face block at offset 450
        assert 450 < 329
    """
    sheet = theme.page_stylesheet()
    first_face = sheet.index("@font-face")
    body_rule = sheet.index("body {")
    assert first_face < body_rule, (
        f"the body rule at offset {body_rule} precedes the first @font-face "
        f"block at offset {first_face}"
    )
    layer_at = sheet.index("@layer")
    assert first_face < layer_at, (
        "an @font-face block is emitted at or after the layer boundary"
    )


def test_no_face_block_reaches_a_network_host():
    """Every src is a same-origin path. The defect this work fixes is a
    face the page never loads and never reports; a CDN src reproduces
    it exactly the first time the machine is offline (DL-163).

    Mutation: the src template was changed to
    https://fonts.gstatic.com/... and this guard rerun. Observed:
        AssertionError: srcs naming a network host:
        ['https://fonts.gstatic.com/IBMPlexSans-Regular.woff2']
    """
    sheet = theme.page_stylesheet()
    remote = sorted(
        src
        for _family, _weight, src in _FACE_BLOCK.findall(sheet)
        if "//" in src or src.startswith("http")
    )
    assert remote == [], f"srcs naming a network host: {remote}"


def test_the_whole_stylesheet_names_no_network_host():
    """No rule anywhere in the emitted sheet fetches from a network
    host - not an @import, not a background image, not a src. The
    artboards carry a fonts.googleapis.com @import, and copying it is
    the shape this guard exists to refuse (DL-163, DL-181).

    Mutation: the artboards' own @import line was pasted at the head of
    page_stylesheet() and this guard rerun. Observed:
        AssertionError: the stylesheet reaches network hosts:
        ['fonts.googleapis.com']
    """
    sheet = theme.page_stylesheet()
    hosts = sorted(set(re.findall(r"https?://([^/'\")\s]+)", sheet)))
    assert hosts == [], f"the stylesheet reaches network hosts: {hosts}"
