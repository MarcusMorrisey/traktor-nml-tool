"""Guards the resolve step's rules as traktor_nml/gui/theme.py emits
them, read out of the returned sheet under the system interpreter, which
has no nicegui.

What a guard here asserts is a rule's own declaration. What it cannot
assert is that the browser laid the step out that way: theme.FONT_SANS
named IBM Plex throughout the period the page painted Segoe UI, so a
guard that reads a name is true in exactly the broken state. The resolved
column widths, the rail's rendered width and the rail's position across
the page region belong to the served-page record (DL-189).

That every .wizard-* class the sheet defines reaches app.py is already
swept by tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py,
so no guard here repeats it.
"""

from __future__ import annotations

import re

from traktor_nml.gui import theme


def _rule(selector: str) -> str:
    """Everything the sheet declares for one selector, as one block.

    Read out of page_stylesheet()'s return value rather than out of
    theme.py's source, so a constant renamed or a value interpolated from
    somewhere else is still read as the sheet emits it. The selector is
    anchored on a brace so `.wizard-answer` does not also collect
    `.wizard-answer-chosen`'s block.

    A selector the sheet emits no rule for fails here as a missing rule
    rather than reading back as an empty declaration, so a guard below
    asserting what a rule contains cannot pass over a rule that is not
    emitted at all.
    """
    blocks = re.findall(
        re.escape(selector) + r"\s*\{([^}]*)\}", theme.page_stylesheet()
    )
    assert blocks, f"the stylesheet emits no {selector} rule"
    return "".join(blocks)


def test_the_split_declares_the_content_column_beside_the_400px_rail():
    """Resolve.dc.html:53's .split is
    `grid-template-columns: 1fr 400px`, the content column taking what is
    left beside a rail at a fixed width, and the sheet declares the same
    two tracks. The flexible one is written `minmax(0, 1fr)`: a bare
    `1fr` track takes an automatic minimum of its own content, so a cell
    holding a path that does not wrap widens the track past the column
    the split stands in and the page scrolls sideways (DL-223).

    Mutation: DETAIL_RAIL_WIDTH was changed from "400px" to "360px" in
    theme.py and this guard rerun. Observed:
        E       AssertionError: assert '360px' == '400px'
        E
        E         - 400px
        E         + 360px
    """
    assert theme.DETAIL_RAIL_WIDTH == "400px"
    assert "grid-template-columns: minmax(0, 1fr) 400px" in _rule(
        ".wizard-resolve-split"
    ), ".wizard-resolve-split declares tracks other than minmax(0, 1fr) 400px"
    assert "display: grid" in _rule(".wizard-resolve-split")


def test_the_conflict_grid_declares_the_five_tracks_the_artboard_draws():
    """Resolve.dc.html:55's .gr is `grid-template-columns: minmax(0,1fr)
    108px 72px 164px 120px` - the track column taking what is left and
    four fixed columns beside it - and the sheet declares the same five.

    The four fixed tracks total 464px, which is what leaves the flexible
    track a usable width inside a table that is itself inside
    .wizard-content-width beside a 400px rail. A guard cannot read that
    arithmetic: the resolved track widths belong to the served-page
    record.

    Mutation: the third track was changed from 72px to 96px in
    CONFLICT_GRID_TRACKS in theme.py and this guard rerun. Observed:
        E       AssertionError: assert 'minmax(0, 1f...x 164px 120px' == 'minmax(0, 1f...x 164px 120px'
        E
        E         - minmax(0, 1fr) 108px 72px 164px 120px
        E         + minmax(0, 1fr) 108px 96px 164px 120px
    """
    assert theme.CONFLICT_GRID_TRACKS == "minmax(0, 1fr) 108px 72px 164px 120px"
    assert (
        f"grid-template-columns: {theme.CONFLICT_GRID_TRACKS}"
        in _rule(".wizard-conflict-grid")
    ), ".wizard-conflict-grid declares tracks other than the artboard's five"


def test_the_track_cell_shortens_inside_its_track_rather_than_crossing_it():
    """Resolve.dc.html:62's .trk carries `overflow: hidden`,
    `text-overflow: ellipsis` and `white-space: nowrap`, and the sheet
    declares all three on .wizard-conflict-track.

    The cell holds a collection path, which offers no break opportunity,
    so a flexible track narrower than the path is not a cell that wraps:
    it is a cell whose text crosses the tracks beside it. min-width: 0 on
    the row's cells lets the track hold its declared width; these three
    are what keep the text inside it.

    Mutation: `text-overflow: ellipsis; ` was removed from the
    .wizard-conflict-track rule in page_stylesheet() and this guard
    rerun. Observed:
        E       AssertionError: .wizard-conflict-track must shorten its text, not let it cross the tracks beside it
        E       assert 'text-overflow: ellipsis' in ' overflow: hidden; white-space: nowrap; '
    """
    track = _rule(".wizard-conflict-track")
    assert "text-overflow: ellipsis" in track, (
        ".wizard-conflict-track must shorten its text, not let it cross "
        "the tracks beside it"
    )
    assert "white-space: nowrap" in track
    assert "overflow: hidden" in track


def test_the_header_row_sits_on_the_same_tracks_as_the_body_rows():
    """Resolve.dc.html:56's .th is a modifier on .gr rather than a grid of
    its own, so the header row and the body rows are laid out on one set
    of tracks. The sheet's header rule therefore declares the row's own
    ground and rule and no tracks at all, and its cells carry the mono
    label the artboard draws.

    A header rule declaring tracks of its own is the failure this holds:
    two grids drift, and a heading stops standing over its column.

    Mutation: `grid-template-columns: 1fr 1fr 1fr 1fr 1fr; ` was added to
    the .wizard-conflict-header rule in page_stylesheet() and this guard
    rerun. Observed:
        E       AssertionError: the header row must take .wizard-conflict-grid's tracks, not declare its [...]
        E       assert 'grid-template-columns' not in ' grid-templ...d: #1F2225; '
        E
        E         'grid-template-columns' is contained here:
        E            grid-template-columns: 1fr 1fr 1fr 1fr 1fr; border-bottom: 1px solid #3C4248; backg [...]
        E         ?  +++++++++++++++++++++
    """
    header = _rule(".wizard-conflict-header")
    assert "grid-template-columns" not in header, (
        "the header row must take .wizard-conflict-grid's tracks, not declare its own"
    )
    assert f"background: {theme.SURFACE_3}" in header
    assert f"border-bottom: 1px solid {theme.BORDER_STRONG}" in header
    assert theme.FONT_MONO in _rule(".wizard-conflict-header > *")


def test_the_detail_rail_carries_its_three_bands():
    """Resolve.dc.html:70 draws .det as a bordered column and :71, :74 and
    :87 draw its head, its body and its footer. The sheet emits one rule
    per band, each carrying the inset and the edge rule that separates it
    from the band beside it, and the rail itself carries no width: it
    takes the second track of .wizard-resolve-split, so the 400px is
    written once.

    Mutation: `width: {DETAIL_RAIL_WIDTH}; ` was added to the
    .wizard-detail-rail rule in page_stylesheet() and this guard rerun.
    Observed:
        E       AssertionError: the rail takes its width from the split's second track
        E       assert 'width' not in ' width: 400...ow: hidden; '
        E
        E         'width' is contained here:
        E            width: 400px; border: 1px solid #2F5A72; border-radius: 8px; background: #141C21; d [...]
        E         ?  +++++
    """
    rail = _rule(".wizard-detail-rail")
    assert "flex-direction: column" in rail
    assert "width" not in rail, (
        "the rail takes its width from the split's second track"
    )
    assert f"border-bottom: 1px solid {theme.BORDER_SUBTLE_5}" in _rule(
        ".wizard-detail-head"
    )
    assert "flex: 1" in _rule(".wizard-detail-body")
    assert f"border-top: 1px solid {theme.BORDER_SUBTLE_5}" in _rule(
        ".wizard-detail-foot"
    )


def test_the_answer_control_carries_its_chosen_state_as_its_own_rule():
    """Resolve.dc.html:77's .cand and :78's .cand.on: one control per
    answer, and the chosen one's own border and ground. The chosen rule is
    declared after the base rule, so the chosen border wins at equal
    specificity, and the dot the chosen marker carries is its own rule
    rather than a pseudo-element, since a call site can name a class and
    cannot name a ::after (DL-189).

    Mutation: the .wizard-answer-chosen rule was moved above the
    .wizard-answer rule in page_stylesheet() and this guard rerun.
    Observed:
        E       AssertionError: the chosen rule must be declared after the base rule
        E       assert 20675 > 20745
        E        +  where 20675 = <built-in method index of str object at [...]
        E        +  and   20745 = <built-in method index of str object at [...]
    """
    sheet = theme.page_stylesheet()
    assert sheet.index(".wizard-answer-chosen {") > sheet.index(".wizard-answer {"), (
        "the chosen rule must be declared after the base rule"
    )
    assert f"background: {theme.ACTION}" in _rule(".wizard-answer-dot")
    assert f"width: {theme.ANSWER_MARKER_SIZE}" in _rule(".wizard-answer-marker")


def test_the_step_rail_carries_the_artboards_span_declaration():
    """Resolve.dc.html:104's .steprail carries `grid-column: 1 / -1`, and
    the sheet carries the same declaration for fidelity with the
    artboard's rule.

    The declaration is inert as the sheet stands, and this guard claims
    no more than that it is present: `grid-column` applies to a grid
    item, and the rail's parent `.wizard-middle` is
    `display: flex; flex-direction: column`, so the rail runs the
    region's width because a flex column stretches it rather than
    because of this rule. The artboard's own `main` is a single-column
    grid, where the declaration is equally inert. A name claiming the
    rail spans the region would be claiming a rendered fact this
    reading knows to be produced by something else (DL-165, DL-189,
    DL-199).

    Mutation: `grid-column: 1 / -1; ` was deleted from the
    .wizard-step-rail rule in page_stylesheet() and this guard rerun.
    Observed:
        E       AssertionError: the step rail must span the page region's columns
        E       assert 'grid-column: 1 / -1' in ' display: flex; gap: 2px; align-items: center; '
    """
    rail = _rule(".wizard-step-rail")
    assert "grid-column: 1 / -1" in rail, (
        "the step rail must span the page region's columns"
    )
    assert "display: flex" in rail


def test_the_current_step_marker_carries_the_action_ground_and_the_page_ink():
    """Resolve.dc.html:26's .st.now .num: the current step's marker
    carries the action blue as its ground and the page ground as its ink.
    It is its own class rather than a rule descending from the current
    step, so the ink is read against the ground the marker paints.

    Mutation: `background: {ACTION}; ` was deleted from the
    .wizard-step-number-current rule in page_stylesheet() and this guard
    rerun. Observed:
        E       AssertionError: the current marker must carry the action ground under its ink
        E       assert 'background: #56B4E9' in ' border-color: #56B4E9; color: #0F1113; '
    """
    marker = _rule(".wizard-step-number-current")
    assert f"background: {theme.ACTION}" in marker, (
        "the current marker must carry the action ground under its ink"
    )
    assert f"color: {theme.GROUND}" in marker
    assert f"width: {theme.STEP_MARKER_SIZE}" in _rule(".wizard-step-number")


def test_the_step_rail_leaves_the_content_columns_centring_intact():
    """The step rail carries .wizard-content-width in app.py, alongside
    the .wizard-card sections of the step it labels, so it must centre in
    the page region with them. .wizard-content-width centres by
    `margin-left: auto; margin-right: auto`, and .wizard-step-rail is
    emitted after it at equal specificity, so any horizontal margin the
    rail declares wins and pins the rail to the region's left edge. This
    reads every declaration in the rail's own block and rejects the
    margin shorthand and both horizontal longhands outright: `margin: 0`
    on a nav loses nothing, and an intended inset would be padding.

    Mutation: `margin: 0; ` was put back into the .wizard-step-rail rule
    in page_stylesheet() and this guard rerun. Observed:
        E       AssertionError: .wizard-step-rail declares margin, which overrides .wizard-content-width's auto margins and stops the rail centring with its column
        E       assert ['margin'] == []
        E
        E         Left contains one more item: 'margin'
        E         Use -v to get more diff
    """
    assert "margin-left: auto" in _rule(".wizard-content-width")
    assert "margin-right: auto" in _rule(".wizard-content-width")
    offenders = [
        declaration.split(":", 1)[0].strip()
        for declaration in _rule(".wizard-step-rail").split(";")
        if declaration.split(":", 1)[0].strip()
        in {"margin", "margin-left", "margin-right", "margin-inline",
            "margin-inline-start", "margin-inline-end"}
    ]
    assert offenders == [], (
        ".wizard-step-rail declares "
        + ", ".join(offenders)
        + ", which overrides .wizard-content-width's auto margins and stops"
        " the rail centring with its column"
    )


def test_every_split_puts_its_rail_at_one_width():
    """Three steps stand a column beside a rail - the resolve step's
    conflict table beside its detail rail, and the preview and write
    steps beside their own second column - and Preview.dc.html:27,
    Write.dc.html:27 and Resolve.dc.html:53 draw all three at the same
    rail width. Both rules read DETAIL_RAIL_WIDTH, so the three cannot
    drift apart (DL-216).

    Both write the flexible track as `minmax(0, 1fr)`, because a bare
    `1fr` takes an automatic minimum of its own content: the set-up
    step's fields hold collection paths that do not wrap, and under a
    bare `1fr` the track grew to 879px inside a 1024px column and the
    page scrolled sideways (DL-223).

    Mutation: .wizard-step-split's flexible track was written as a bare
    `1fr`. Observed:
        E           AssertionError: .wizard-step-split declares no two-track split
        E           assert None is not None
    """
    for name in (".wizard-resolve-split", ".wizard-step-split"):
        tracks = re.search(
            r"grid-template-columns:\s*minmax\(0, 1fr\)\s*([^;]+);", _rule(name)
        )
        assert tracks is not None, f"{name} declares no two-track split"
        assert tracks.group(1).strip() == theme.DETAIL_RAIL_WIDTH, (
            tracks.group(1).strip()
        )
    # The step split stands inside a column the framework lays out with
    # its items packed to the start, so a grid taking its own content's
    # width sits narrower than the column and its rail leaves the
    # column's right edge. It takes the column's width instead (DL-223).
    assert "width: 100%" in _rule(".wizard-step-split"), (
        ".wizard-step-split takes its content's width rather than its column's"
    )
    # The same reading for the row a path stands in: the source list is a
    # framework column that packs its rows to the start, so a row taking
    # its own path's width spills past the card that holds it - read at
    # 727px inside a 604px card before this (DL-223).
    assert "width: 100%" in _rule(".wizard-field-row"), (
        ".wizard-field-row takes its path's width rather than its row's"
    )
