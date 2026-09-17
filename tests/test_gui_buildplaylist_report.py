"""Guards the build-playlist report's grid and its kind pills: the tracks,
the header rule and the pill rule per kind the sheet emits, and that
traktor_nml/gui/app.py builds the header row, every body row and the kind
cell's pill on that grid, read under the system interpreter, which has no
nicegui.

A sheet guard alone is green in the state where the page never applies the
rule, so the page guards read app.py's source for the call sites (DL-189).
Neither can read what the browser laid out: the resolved column edges, the
rules and the truncation are read on a served page in
docs/2026-09-17-report-columns-browser-record.md (DL-084, DL-169, DL-302),
and the pills' colours, shape and width against the Kind column in
docs/2026-09-17-report-kind-pills-browser-record.md (DL-304).

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation, with the trailing spaces pytest
printed on its blank `E` lines trimmed.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from traktor_nml.gui import buildplaylist_view, theme

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def _rule(selector: str) -> str:
    """Everything the sheet declares for one selector, as one block."""
    blocks = re.findall(
        re.escape(selector) + r"\s*\{([^}]*)\}", theme.page_stylesheet()
    )
    assert blocks, f"the stylesheet emits no {selector} rule"
    return " ".join(blocks)


def test_the_report_grid_declares_the_artboards_three_tracks_and_header_label():
    """design/build-playlist/Specs.dc.html:178 draws the header cells `#` at
    64px, Entry taking the rest and Kind at 120px, and :57 gives each th a
    600 11px/1 mono label, uppercase, at #8E979E over a 1px #2A2E32 rule.
    The sheet declares those three tracks on the grid both rows share, no
    tracks on the header modifier, the label on the header's cells, and
    :59's last row with no rule.

    Mutation: REPORT_GRID_TRACKS in theme.py was changed from
    "64px minmax(0, 1fr) 120px" to "64px minmax(0, 1fr) 96px" and this
    guard rerun. Observed:
        E       AssertionError: assert '64px minmax(0, 1fr) 96px' == '64px minmax(0, 1fr) 120px'
        E
        E         - 64px minmax(0, 1fr) 120px
        E         ?                     ^^^
        E         + 64px minmax(0, 1fr) 96px
        E         ?                     ^^
    """
    assert theme.REPORT_GRID_TRACKS == "64px minmax(0, 1fr) 120px"
    assert (
        f"grid-template-columns: {theme.REPORT_GRID_TRACKS}"
        in _rule(".buildplaylist-report-grid")
    )
    header = _rule(".buildplaylist-report-header")
    assert "grid-template-columns" not in header, (
        "the header row must take .buildplaylist-report-grid's tracks, not declare its own"
    )
    assert f"border-bottom: 1px solid {theme.BORDER}" in header
    label = _rule(".buildplaylist-report-header > *")
    assert f"font: 600 {theme.TYPE_11}/1 {theme.FONT_MONO}" in label
    assert "text-transform: uppercase" in label
    assert "letter-spacing: .06em" in label
    assert f"color: {theme.TEXT_FAINT}" in label
    assert f"border-bottom: 1px solid {theme.SURFACE_5}" in _rule(".buildplaylist-report-row")
    assert "border-bottom: 0" in _rule(".buildplaylist-report-row:last-child")
    assert "min-width: 0" in _rule(".buildplaylist-report-row > *")
    entry = _rule(".buildplaylist-report-entry")
    assert "text-overflow: ellipsis" in entry
    assert "white-space: nowrap" in entry
    assert "overflow: hidden" in entry


def test_each_kind_pill_carries_the_artboards_tint_on_the_shared_pill_shape():
    """design/build-playlist/Specs.dc.html:60 shapes .kind as a 600
    11px/1 mono pill, uppercase at .04em, 3px by 6px inside a 4px
    radius and never wrapped, and :61-63 give the three kinds their own
    text hue, tinted ground and 1px border. The sheet declares the
    shape once on the class every pill carries and each kind's three
    colours on its own rule, and the shared rule sets no colour or
    border of its own so a kind with no tint rule still reads.

    Mutation: the unmatched pill's background in theme.py was changed
    from REPORT_KIND_UNMATCHED_TINT_BG to STATUS_NOT_FOUND_TINT_BG -
    the nearest-named token, and a different colour - and this guard
    rerun. Observed:
        E           AssertionError: unmatched
        E           assert 'background: #2B1D14' in ' color: #E07A4C; background: #21160F; border: 1px solid #5A3A24; '
    """
    shared = _rule(f".{buildplaylist_view.KIND_PILL_BASE_CLASS}")
    assert f"font: 600 {theme.TYPE_11}/1 {theme.FONT_MONO}" in shared
    assert "text-transform: uppercase" in shared
    assert "letter-spacing: .04em" in shared
    assert f"padding: {theme.SPACE_3} {theme.SPACE_6}" in shared
    assert f"border-radius: {theme.RADIUS_SM}" in shared
    assert "white-space: nowrap" in shared
    # The pill hugs its word rather than filling the 120px Kind track.
    assert "display: inline-block" in shared
    assert "color:" not in shared, "the shared pill rule fixes a colour each kind sets"
    assert "border:" not in shared, "the shared pill rule fixes a border each kind sets"
    expected = {
        "unmatched": (
            theme.STATUS_NOT_FOUND,
            theme.REPORT_KIND_UNMATCHED_TINT_BG,
            theme.REPORT_KIND_UNMATCHED_TINT_BORDER,
        ),
        "ambiguous": (
            theme.STATUS_NEEDS_REVIEW,
            theme.STATUS_NEEDS_REVIEW_TINT_BG,
            theme.STATUS_NEEDS_REVIEW_STRONG,
        ),
        "unparseable": (
            theme.TEXT_SUBTLE_1,
            theme.REPORT_KIND_UNPARSEABLE_TINT_BG,
            theme.BORDER_STRONG,
        ),
    }
    for kind, (colour, background, border) in expected.items():
        body = _rule(f".{buildplaylist_view.KIND_PILL_BASE_CLASS}-{kind}")
        assert f"color: {colour}" in body, kind
        assert f"background: {background}" in body, kind
        assert f"border: 1px solid {border}" in body, kind


_TRACKLIST_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "tracklist.py"
_BUILDPLAYLIST_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "buildplaylist.py"


def _model_kinds() -> set:
    """Every UnresolvedRow.kind a run can produce, read from
    tracklist.resolve_candidates - the one function that decides a
    candidate's outcome - rather than restated here, so an outcome
    added to it arrives in the guard below on its own. Sound only while
    buildplaylist._resolve_lines copies that outcome into kind for
    every outcome but `matched`, which the guard also checks."""
    module = ast.parse(_TRACKLIST_PY.read_text(encoding="utf-8"))
    resolve = next(
        node
        for node in ast.walk(module)
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_candidates"
    )
    outcomes = {
        keyword.value.value
        for node in ast.walk(resolve)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "outcome"
        and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
    }
    assert outcomes, "no outcome= literal read from resolve_candidates"
    return outcomes - {"matched"}


def test_every_kind_the_model_can_produce_has_a_pill_rule():
    """The kinds are read from tracklist.resolve_candidates' own
    outcome= literals, so a kind added there fails here rather than
    reaching the report with no tint. Each one is named by
    buildplaylist_view's closed kind-to-class mapping and has a rule of
    that name in the sheet.

    Mutation: `outcome="ambiguous"` in tracklist.resolve_candidates was
    changed to `outcome="tied"`, standing in for a kind added to the
    model with no pill rule of its own, and this guard rerun. Observed:
        E       AssertionError: the kind-to-class mapping and the kinds the model produces differ
        E       assert {'ambiguous',...'unparseable'} == {'tied', 'unm...'unparseable'}
        E
        E         Extra items in the left set:
        E         'ambiguous'
        E         Extra items in the right set:
        E         'tied'
        E         Use -v to get more diff
    """
    assert "kind=resolution.outcome" in _BUILDPLAYLIST_PY.read_text(encoding="utf-8"), (
        "_resolve_lines no longer carries the resolution's outcome as the row's kind, "
        "so resolve_candidates is not the source of truth these kinds are read from"
    )
    kinds = _model_kinds()
    assert set(buildplaylist_view.KIND_PILL_CLASSES) == kinds, (
        "the kind-to-class mapping and the kinds the model produces differ"
    )
    for kind in sorted(kinds):
        classes = buildplaylist_view.kind_pill_classes(kind)
        assert classes.split() == [
            buildplaylist_view.KIND_PILL_BASE_CLASS,
            f"{buildplaylist_view.KIND_PILL_BASE_CLASS}-{kind}",
        ], kind
        _rule(f".{buildplaylist_view.KIND_PILL_BASE_CLASS}-{kind}")
    # A kind the mapping does not name keeps the pill's shape and the
    # row's ink rather than raising or going unstyled.
    assert buildplaylist_view.kind_pill_classes("wedged") == (
        buildplaylist_view.KIND_PILL_BASE_CLASS
    )


def _fill_function() -> ast.With:
    """The `with report_table:` block inside _build_build_playlist_page,
    where the report's rows are built."""
    module = ast.parse(_APP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_build_playlist_page":
            page = node
            break
    else:
        raise AssertionError("app.py defines no _build_build_playlist_page")
    for node in ast.walk(page):
        if isinstance(node, ast.With) and any(
            isinstance(item.context_expr, ast.Name) and item.context_expr.id == "report_table"
            for item in node.items
        ):
            return node
    raise AssertionError("_build_build_playlist_page never enters report_table")


def _element_classes(with_node: ast.With) -> str:
    """The class string of `with ui.element(...).classes("...")`, or ""."""
    call = with_node.items[0].context_expr
    if (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "classes"
        and call.args
        and isinstance(call.args[0], ast.Constant)
    ):
        return str(call.args[0].value)
    return ""


def test_the_page_builds_the_header_and_every_row_inside_the_report_grid():
    """app.py enters report_table and, directly inside it, builds one
    header row carrying `buildplaylist-report-grid
    buildplaylist-report-header` whose cells are the labels
    REPORT_COLUMN_LABELS names, and, in the loop over the rows, one
    `buildplaylist-report-grid buildplaylist-report-row` per row holding
    three cells, the entry cell carrying `buildplaylist-report-entry`.

    Mutation: the body row's class string in app.py was changed from
    "buildplaylist-report-grid buildplaylist-report-row" to "gap-3" and
    this guard rerun. Observed:
        E       AssertionError: a body row is built outside the report grid
        E       assert 'gap-3' == 'buildplaylis...st-report-row'
        E
        E         - buildplaylist-report-grid buildplaylist-report-row
        E         + gap-3
    """
    assert buildplaylist_view.REPORT_COLUMN_LABELS == ("#", "Entry", "Kind")
    fill = _fill_function()
    withs = [node for node in fill.body if isinstance(node, ast.With)]
    fors = [node for node in fill.body if isinstance(node, ast.For)]
    assert len(withs) == 1, "the report holds no header row of its own"
    assert (
        _element_classes(withs[0]) == "buildplaylist-report-grid buildplaylist-report-header"
    ), "the header row is built outside the report grid"
    header_source = ast.unparse(withs[0])
    assert "buildplaylist_view.REPORT_COLUMN_LABELS" in header_source
    assert len(fors) == 1, "the report builds its body rows in no loop"
    rows = [node for node in fors[0].body if isinstance(node, ast.With)]
    assert len(rows) == 1
    assert (
        _element_classes(rows[0]) == "buildplaylist-report-grid buildplaylist-report-row"
    ), "a body row is built outside the report grid"
    cells = rows[0].body
    assert len(cells) == 3, "a body row carries other than the header's three cells"
    assert "buildplaylist-report-entry" in ast.unparse(cells[1])


def test_the_page_builds_the_kind_cell_as_a_pill_classed_from_the_row_kind():
    """A stylesheet rule the page never applies is green in the sheet
    guard above, so this reads app.py for the kind cell itself (DL-189):
    the third cell of the body row holds a pill element whose classes
    come from buildplaylist_view.kind_pill_classes called on the loop's
    own kind and whose text comes from kind_pill_label, so every row
    carries the class the sheet gives that row's kind.

    Mutation: the pill's classes() argument in app.py was changed from
    buildplaylist_view.kind_pill_classes(kind) to the literal
    "buildplaylist-report-kind buildplaylist-report-kind-unmatched", so
    every row would carry one kind's tint, and this guard rerun.
    Observed:
        E       AssertionError: the kind pill's classes are not derived from the row's kind
        E       assert 'buildplaylist_view.kind_pill_classes(kind)' in "ui.label(buildplaylist_view.kind_pill_label(kind)).classes('buildplaylist-report-kind buildplaylist-report-kind-unmatched')"
    """
    fill = _fill_function()
    loop = next(node for node in fill.body if isinstance(node, ast.For))
    kind_name = loop.target.elts[2].id
    row = next(node for node in loop.body if isinstance(node, ast.With))
    cell = row.body[2]
    assert isinstance(cell, ast.With), "the kind cell holds no element of its own"
    pill = ast.unparse(cell.body)
    assert f"buildplaylist_view.kind_pill_classes({kind_name})" in pill, (
        "the kind pill's classes are not derived from the row's kind"
    )
    assert f"buildplaylist_view.kind_pill_label({kind_name})" in pill
    assert "classes" in pill


def test_a_run_that_leaves_rows_scrolls_the_report_card_into_view():
    """write_playlist calls ui.run_javascript with scrollIntoView on
    report_section's element, inside an `if rows:` and after the report's
    rows are built, so a run that leaves unresolved rows brings the card
    below the fold of wizard-middle into view and a run with none does not
    scroll. A view helper alone is green when the page never calls it, so
    this reads app.py (DL-189, DL-303). That the middle region scrolls and
    the document does not is read in
    docs/2026-09-17-report-scroll-and-encoding-browser-record.md.

    Mutation: `if rows:` above the scroll call in app.py was changed to
        `if True:` and this guard rerun.
    Observed:
        E       AssertionError: the scroll is not gated on rows existing
        E       assert 'True' == 'rows'
        E
        E         - rows
        E         + True
    """
    module = ast.parse(_APP_PY.read_text(encoding="utf-8"))
    write = next(
        node
        for node in ast.walk(module)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "write_playlist"
    )
    fill = next(
        index
        for index, node in enumerate(write.body)
        if isinstance(node, ast.With) and "report_table" in ast.unparse(node.items[0].context_expr)
    )
    gated = [
        node
        for node in write.body
        if isinstance(node, ast.If)
        and "scrollIntoView" in ast.unparse(node)
    ]
    assert len(gated) == 1, "write_playlist scrolls to the report under no condition of its own"
    scroll = gated[0]
    assert ast.unparse(scroll.test) == "rows", "the scroll is not gated on rows existing"
    assert not scroll.orelse
    source = ast.unparse(scroll.body)
    assert "ui.run_javascript" in source
    assert "report_section.id" in source
    assert write.body.index(scroll) > fill, "the scroll runs before the rows are built"
    outside = [node for node in write.body if node is not scroll]
    assert not any("scrollIntoView" in ast.unparse(node) for node in outside)
