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
    two tracks.

    Mutation: DETAIL_RAIL_WIDTH was changed from "400px" to "360px" in
    theme.py and this guard rerun. Observed:
        E       AssertionError: assert '360px' == '400px'
        E
        E         - 400px
        E         + 360px
    """
    assert theme.DETAIL_RAIL_WIDTH == "400px"
    assert "grid-template-columns: 1fr 400px" in _rule(".wizard-resolve-split"), (
        ".wizard-resolve-split declares tracks other than 1fr 400px"
    )
    assert "display: grid" in _rule(".wizard-resolve-split")


def test_the_conflict_grid_declares_the_five_tracks_the_artboard_draws():
    """Resolve.dc.html:55's .gr is `grid-template-columns: minmax(0,1fr)
    132px 84px 196px 140px` - the track column taking what is left and
    four fixed columns beside it - and the sheet declares the same five.

    Mutation: the third track was changed from 84px to 96px in
    CONFLICT_GRID_TRACKS in theme.py and this guard rerun. Observed:
        E       AssertionError: assert 'minmax(0, 1f...x 196px 140px' == 'minmax(0, 1f...x 196px 140px'
        E
        E         - minmax(0, 1fr) 132px 84px 196px 140px
        E         ?                      ^^
        E         + minmax(0, 1fr) 132px 96px 196px 140px
        E         ?                      ^^
    """
    assert theme.CONFLICT_GRID_TRACKS == "minmax(0, 1fr) 132px 84px 196px 140px"
    assert (
        f"grid-template-columns: {theme.CONFLICT_GRID_TRACKS}"
        in _rule(".wizard-conflict-grid")
    ), ".wizard-conflict-grid declares tracks other than the artboard's five"


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
