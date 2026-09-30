"""Guards the settled reading on the reconstruct page's preview step: the
classes app.py passes for it, the rules theme.page_stylesheet() declares
for those classes, and the artboard the two are built to.

A guard reading a class name is true in exactly the broken state, so what
the browser resolved from those names is read on a served page and
written into docs/2026-09-26-tiered-conflict-browser-record.md, whose
verdict-row digest is registered in
tests/test_docs_browser_record_structure.py (DL-084, DL-169, DL-189).
What this file can close is narrower and exact: every class named in the
page expands to a rule in the sheet, and no dimension or hex for the
reading stands in the page (DL-069, DL-188).

theme.py imports no framework, so these run under the system interpreter
with no nicegui.

app.py is read as text and as an AST here rather than imported, because
importing it would import nicegui, which the system interpreter does not
hold: the classes the page passes are read out of the source and matched
against the sheet's own rules, which is the pairing a guard can close
without a browser (DL-069, DL-189).

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation. This file is LF, like the rest of
tests/.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from traktor_nml.gui import theme

_ROOT = Path(__file__).resolve().parents[1]
_APP_PY = _ROOT / "traktor_nml" / "gui" / "app.py"
_ARTBOARD = _ROOT / "design" / "reconnect-wizard" / "Preview.dc.html"

# The classes the reading is drawn with. Named rather than discovered, so
# a class dropped from the page fails this file rather than shrinking the
# set it checks - a guard green in exactly the broken state (DL-189).
READING_CLASSES = (
    "wizard-callout-info",
    "wizard-outlier-row",
    "wizard-outlier-name",
    "wizard-outlier-key",
    "wizard-outlier-values",
    "wizard-outlier-winner",
    "wizard-outlier-gap",
)


def _sheet() -> str:
    return theme.page_stylesheet()


def _source() -> str:
    return _APP_PY.read_text(encoding="utf-8")


def _named_function(name: str) -> ast.FunctionDef:
    for node in ast.walk(ast.parse(_source())):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    raise AssertionError(f"app.py defines no {name}")


def _declares(name: str, sheet: str) -> bool:
    return bool(re.search(rf"\.{re.escape(name)}\b\s*[,{{:]", sheet))


@pytest.mark.parametrize("name", READING_CLASSES)
def test_every_class_the_reading_names_expands_to_a_rule(name):
    """A class string the sheet does not declare draws an unstyled row and
    no import fails, which is why the cascade is read here rather than
    left to the page (DL-069).

    Fail-first mutation: the .wizard-outlier-winner rule removed from
    page_stylesheet().
    Observed:
        E       AssertionError: page_stylesheet() declares no .wizard-outlier-winner
        E       assert False
        E        +  where False = _declares('wizard-outlier-winner', "\\n@font-face { font-family: 'IBM Plex Sans'; font-style: normal; font-weight: 400; font-display: block; src: url('/fo...izard-control, .wizard-field-row > .wizard-control, .buildplaylist-input-row > .wizard-control { margin-bottom: 0; }\\n")
        E        +    where "\\n@font-face { font-family: 'IBM Plex Sans'; font-style: normal; font-weight: 400; font-display: block; src: url('/fo...izard-control, .wizard-field-row > .wizard-control, .buildplaylist-input-row > .wizard-control { margin-bottom: 0; }\\n" = _sheet()
        tests\\test_gui_settled_reading.py:93: AssertionError
    """
    assert _declares(name, _sheet()), f"page_stylesheet() declares no .{name}"


def test_the_page_names_no_class_the_sheet_does_not_declare():
    """Read the other way round: every class app.py passes for the
    settled reading is one the sheet declares, so a typo in a class
    string fails here rather than on a served page.

    Fail-first mutation: "wizard-outlier-gaps" passed for the gap cell in
    app.py's outlier_row.
    Observed:
        E       AssertionError: app.py names classes the sheet does not declare: ['wizard-outlier-gaps']
        E       assert ['wizard-outlier-gaps'] == []
        E
        E         Left contains one more item: 'wizard-outlier-gaps'
        E         Use -v to get more diff
        tests\\test_gui_settled_reading.py:126: AssertionError
    """
    sheet = _sheet()
    named: set[str] = set()
    for node in ast.walk(ast.parse(_source())):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "classes"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            for name in node.args[0].value.split():
                if name.startswith("wizard-outlier") or name == "wizard-callout-info":
                    named.add(name)
    missing = sorted(name for name in named if not _declares(name, sheet))
    assert missing == [], (
        f"app.py names classes the sheet does not declare: {missing}"
    )


def test_the_page_names_every_class_the_reading_is_drawn_with():
    """The other half of the pairing: a cell dropped from outlier_row
    leaves its rule standing in the sheet with nothing carrying it, which
    is a reading missing a line rather than an unstyled one.

    Fail-first mutation: the winner cell's ui.label removed from
    outlier_row.
    Observed:
        E       AssertionError: the page draws no ['wizard-outlier-winner']
        E       assert ['wizard-outlier-winner'] == []
        E
        E         Left contains one more item: 'wizard-outlier-winner'
        E         Use -v to get more diff
        tests\\test_gui_settled_reading.py:152: AssertionError
    """
    source = _source()
    absent = [
        name
        for name in READING_CLASSES
        if not re.search(rf'"[^"]*\b{re.escape(name)}\b[^"]*"', source)
    ]
    assert absent == [], f"the page draws no {absent}"


def test_the_listing_row_stacks_four_areas_against_the_gap_column():
    """The gap holds its own column against all four stacked cells, which
    is why the row is a grid with named areas rather than a flex column.
    The winner area is one of the four: the row names the record the
    output keeps (DL-148).

    Fail-first mutation: grid-template-areas left at the three-area
    string "name gap" "key gap" "values gap".
    Observed:
        E           assert '"winner gap"' in '.wizard-outlier-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "name gap" "key gap" "values gap"; gap: 2px 12px; align-items: center; padding: 8px 2px; font-size: 12.5px; }'
        tests\\test_gui_settled_reading.py:171: AssertionError
    """
    sheet = _sheet()
    rule = re.search(r"\.wizard-outlier-row\s*\{[^}]*\}", sheet).group(0)
    assert "display: grid" in rule
    for area in ('"name gap"', '"key gap"', '"values gap"', '"winner gap"'):
        assert area in rule
    for cell in ("name", "key", "values", "winner", "gap"):
        assert f"grid-area: {cell}" in sheet, f"no cell claims grid-area: {cell}"


def test_the_listing_draws_its_separator_between_rows():
    """The settled sentence stands in the same container as the rows and
    follows them, so the last row is never its parent's last child. The
    rule that ends the list is a top border on every row after the first:
    an edge no following sibling can defeat. A bottom border on each row
    cancelled by :last-child reads green in the sheet while the served
    page draws a line under the final row (DL-189, DL-325).

    Fail-first mutation: the separator declared the cancelled way -
    `border-bottom: 1px solid {SURFACE_5}` put back inside
    .wizard-outlier-row and `.wizard-outlier-row:last-child {{
    border-bottom: 0; }}` restored in place of the adjacent-sibling rule.
    Observed:
        E       AssertionError: the row itself carries the separator
        E       assert 'border' not in '.wizard-out...e: 12.5px; }'
        E
        E         'border' is contained here:
        E            8px 2px; border-bottom: 1px solid #23272B; font-size: 12.5px; }
        E         ?           ++++++
        tests\\test_gui_settled_reading.py:199: AssertionError
    """
    sheet = _sheet()
    rule = re.search(r"\.wizard-outlier-row\s*\{[^}]*\}", sheet).group(0)
    assert "border" not in rule, "the row itself carries the separator"
    between = re.search(
        r"\.wizard-outlier-row \+ \.wizard-outlier-row\s*\{[^}]*\}", sheet
    )
    assert between, "no rule draws a separator between two rows"
    assert "border-top: 1px solid" in between.group(0)
    assert ".wizard-outlier-row:last-child" not in sheet, (
        "a :last-child rule stands that no composition can match"
    )


def test_the_page_holds_no_dimension_hex_or_percentage_for_the_reading():
    """Every pixel size, hue and formatted number for the reading lives in
    theme.py and in the record, so the page is composition alone (DL-069,
    DL-215).

    Fail-first mutation: `.style("color:#F5D96B")` added to the gap
    cell's label in outlier_row.
    Observed:
        E       AssertionError: the outlier row holds a hex, a dimension or a format
        E       assert ['#F5D96B'] == []
        E
        E         Left contains one more item: '#F5D96B'
        E         Use -v to get more diff
        tests\\test_gui_settled_reading.py:228: AssertionError
    """
    block = ast.get_source_segment(_source(), _named_function("outlier_row")) or ""
    assert block, "app.py defines no outlier_row"
    offenders = re.findall(r"#[0-9A-Fa-f]{6}|\d+px|\d+%|:[.,]\d[fd]", block)
    assert offenders == [], (
        "the outlier row holds a hex, a dimension or a format"
    )


def test_the_artboard_draws_the_surfaces_the_page_composes():
    """DL-071: the screen is built to the artboard, so the artboard holds
    the settled note in the .note info tint and the .ol rows with a .w
    cell before the page names their classes.

    Two info notes: the one under the could-not-fill card about the
    playlists left untouched, and the settled note in the left column
    beside the conflict note.

    The artboard's own .meta sentence closes the .card-b the .ol rows
    stand in, so the artboard draws its separator between rows as well:
    the sheet and the screen agree on which edge carries the line.

    Fail-first mutation: the .w span removed from each of the artboard's
    three .ol rows.
    Observed:
        E       assert 0 == 3
        E        +  where 0 = <built-in method count of str object at 0x0000028F5A50EE10>('class="w"')
        E        +    where <built-in method count of str object at 0x0000028F5A50EE10> = '<!doctype html>\\n<html>\\n<head>\\n  <meta charset="utf-8">\\n  <script src="./support.js"></script>\\n</head>\\n<body>\\n<... class="btn btn-pri">Decide the 63 conflicts</button>\\n    </span>\\n  </footer>\\n\\n</div>\\n</x-dc>\\n</body>\\n</html>\\n'.count
        tests\\test_gui_settled_reading.py:257: AssertionError
    """
    artboard = _ARTBOARD.read_text(encoding="utf-8")
    assert artboard.count('class="note info"') == 2
    assert artboard.count('class="ol"') == 3
    assert artboard.count('class="w"') == 3
    rule = re.search(r"^\.ol\{[^}]*\}", artboard, re.MULTILINE).group(0)
    for area in ('"nm g"', '"k g"', '"v g"', '"w g"'):
        assert area in rule
    assert "border" not in rule
    assert ".ol + .ol{border-top:1px solid #23272B}" in artboard
    assert ".ol:last-child" not in artboard
