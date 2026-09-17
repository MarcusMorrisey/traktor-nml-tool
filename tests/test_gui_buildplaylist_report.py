"""Guards the build-playlist report's grid: the tracks and header rule the
sheet emits, and that traktor_nml/gui/app.py builds the header row and
every body row on that grid, read under the system interpreter, which has
no nicegui.

A sheet guard alone is green in the state where the page never applies the
rule, so the second guard reads app.py's source for the call sites (DL-189).
Neither can read what the browser laid out: the resolved column edges, the
rules and the truncation are read on a served page in
docs/2026-09-17-report-columns-browser-record.md (DL-084, DL-169, DL-302).

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
