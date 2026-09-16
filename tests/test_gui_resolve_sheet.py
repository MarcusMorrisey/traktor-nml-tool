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
    :105 draw its head, its body and its footer. The sheet emits one rule
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
    """Resolve.dc.html:81's .cand and :82's .cand.on: one control per
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


# Every class the rail names is declared in theme.py and every
# dimension and colour with it, so no size or colour literal stands in
# app.py (ref: DL-069, DL-078). No rule here conditions a colour on a
# value's magnitude: difference is marked and never ranked
# (ref: DL-249).


def test_the_field_row_declares_the_three_tracks_the_artboard_draws():
    """Resolve.dc.html:90's .cmpf: a fixed key track, a flexible value
    track and a fixed raw track, so every answer's keys align down the
    rail and the raw strings the operator compares stand at one edge.

    Mutation: `grid-template-columns` in .wizard-answer-field was
    changed to `{ANSWER_FIELD_KEY_TRACK} 1fr 1fr` in theme.py and this
    guard rerun. Observed:
        E       AssertionError: assert 'grid-template-columns: 60px 1fr 82px' in ' display: grid; grid-template-columns: 60px 1fr 1fr; gap: 8px; align-items: center; padding: 5px 0; border-bottom: 1px solid #22292E; '
    """
    rule = _rule(".wizard-answer-field")
    assert (
        f"grid-template-columns: {theme.ANSWER_FIELD_KEY_TRACK} 1fr "
        f"{theme.ANSWER_FIELD_RAW_TRACK}"
    ) in rule


def test_the_field_key_and_the_difference_mark_carry_their_own_rules():
    """The key is mono and uppercase (Resolve.dc.html:92) and the mark
    is a dot at its own size (Resolve.dc.html:101), distinct from the
    chosen marker's dot, which means something else.

    Mutation: ANSWER_FIELD_MARK_SIZE was changed to
    ANSWER_MARKER_DOT_SIZE in the .wizard-answer-field-mark rule in
    theme.py and this guard rerun. Observed:
        E       AssertionError: assert 'width: 5px' in ' width: 8px; height: 8px; border-radius: 50%; background: #56B4E9; flex: none; '
    """
    key = _rule(".wizard-answer-field-key")
    assert "text-transform: uppercase" in key and theme.FONT_MONO in key
    mark = _rule(".wizard-answer-field-mark")
    assert f"width: {theme.ANSWER_FIELD_MARK_SIZE}" in mark
    assert theme.ANSWER_FIELD_MARK_SIZE != theme.ANSWER_MARKER_DOT_SIZE


def test_no_rail_rule_colours_a_value_by_its_magnitude():
    """The tool does not know a larger filesize is the better one, so no
    rule on this rail states a colour for a value at all - only for the
    mark that says the answers disagree.

    This is the reading that fails the moment a "the bigger one is
    green" rule is reintroduced, which the user cut explicitly (DL-249).

    Mutation: `.wizard-answer-field-value-larger {{ color:
    {STATUS_FOUND}; }}` was added to page_stylesheet() and this guard
    rerun. Observed:
        E       AssertionError: assert not ['.wizard-answer-field-value-larger']
    """
    sheet = theme.page_stylesheet()
    named = re.findall(r"\.wizard-answer-field[\w-]*", sheet)
    assert not [
        name for name in named
        if any(word in name for word in ("larger", "smaller", "better", "worse"))
    ]
    assert "color:" not in _rule(".wizard-answer-field-value")


def test_the_answer_card_aligns_its_marker_with_the_record_it_heads():
    """Resolve.dc.html:81's .cand aligns its items to the start. The
    answer beside the marker is a block of one row per tracked
    attribute, so a centred marker sits at the middle of the record
    rather than beside any row of it - read on the served page at 103px
    below the card's own top edge, against the 8.8px the start gives.

    The artboard carries the same declaration, so this is the screen
    built to the design rather than against it (DL-071).

    Mutation: `align-items: flex-start` in .wizard-answer was changed
    back to `align-items: center` in theme.py and this guard rerun.
    Observed:
        E       AssertionError: the answer card centres its marker against a block of field rows
        E       assert 'align-items: flex-start' in ' border: 1px solid #2A2E32; background: #12181C; border-radius: 6px; padding: 8px 10px; display: flex; gap: 9px; align-items: center; '
    """
    assert "align-items: flex-start" in _rule(".wizard-answer"), (
        "the answer card centres its marker against a block of field rows"
    )


def test_the_field_block_turns_quasars_button_wrapper_back_into_a_column():
    """A framework shortfall, in the shape DL-223 records: Quasar wraps
    a button's children in its own `.q-btn__content`, so the column
    declared on `.wizard-answer-fields` governs that wrapper and not the
    field rows inside it. The wrapper's own rule is a centred, wrapping
    row, under which each row took its content's width and was centred
    on its own wrap line - six rows read at 165.9px to 209.1px starting
    at six different x positions inside a 400px rail - and the holders
    line shared the last row's wrap line instead of standing under the
    fields. The wrapper's text-center reads the same way sideways: a
    value sat at the centre of its track rather than at its start.

    The rows are the artboard's aligned three-track grid, so the
    wrapper carries the column the block declares. Reading
    `.wizard-answer-fields`' own rule alone is true in exactly that
    broken state, which is why this guard reads the wrapper's.

    Mutation: the `.wizard-answer-fields .q-btn__content` rule was
    deleted from page_stylesheet() in theme.py and this guard rerun.
    Observed:
        E       AssertionError: the stylesheet emits no .wizard-answer-fields .q-btn__content rule
        E       assert []

    Mutation: `text-align: left` alone was dropped from that rule in
    theme.py and this guard rerun. Observed:
        E           AssertionError: the button wrapper the field rows lay out in declares no text-align: left
        E           assert 'text-align: left' in ' width: 100%; flex-direction: column; flex-wrap: nowrap; align-items: stretch; justify-content: flex-start; '
    """
    wrapper = _rule(".wizard-answer-fields .q-btn__content")
    for declaration in (
        "flex-direction: column",
        "flex-wrap: nowrap",
        "align-items: stretch",
        "width: 100%",
        "text-align: left",
    ):
        assert declaration in wrapper, (
            f"the button wrapper the field rows lay out in declares no "
            f"{declaration}"
        )


def test_the_step_rail_carries_the_artboards_span_declaration():
    """Resolve.dc.html:118's .steprail carries `grid-column: 1 / -1`, and
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
