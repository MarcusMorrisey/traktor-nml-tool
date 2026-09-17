"""Guards the build-playlist switches' option rows and the read-only note
under the unresolved report: that the sentences on the screen are the
sentences design/build-playlist/Specs.dc.html draws, that the sheet emits
the option row, its label and the two notes, and that app.py builds each
switch inside an option row with its description beside it and the note
after the report table, read under the system interpreter, which has no
nicegui.

A guard reading only the view module's constants is green in exactly the
state this closes - the sentences defined and the page never building them
- so the page guards read app.py's source for the call sites (DL-189).
The rendered indent, the row's border and where the note sits are read on
a served page in
docs/2026-09-17-switch-options-browser-record.md (DL-084, DL-169, DL-307).

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
_SPECS = (
    Path(__file__).resolve().parents[1]
    / "design"
    / "build-playlist"
    / "Specs.dc.html"
)


def _artboard_text(class_name: str) -> list[str]:
    """Every run of text the artboard puts inside an element of this
    class, with the em dash it typesets folded to the hyphen the screen's
    strings carry and runs of whitespace collapsed."""
    found = []
    for raw in re.findall(
        r'class="' + class_name + r'"[^>]*>(.*?)</', _SPECS.read_text(encoding="utf-8"), re.S
    ):
        text = re.sub(r"<[^>]+>", "", raw)
        text = text.replace("—", "-").replace("’", "'")
        found.append(re.sub(r"\s+", " ", text).strip())
    return found


def test_each_switch_says_what_its_two_states_write():
    """The two option descriptions on the screen are the two .opt-d
    sentences Specs.dc.html:159 and :167 draw, and the note under the
    report is :185's. Read off the artboard rather than repeated here,
    so a sentence edited in the design and not on the screen is caught
    by the same guard that catches the reverse.

    Mutation: FULL_COLLECTION_NOTE in buildplaylist_view.py was cut to
    its first sentence, 'Keep the whole source collection and playlist
    tree in the output.', and this guard rerun. Observed:
        AssertionError: the screen's description is not the artboard's:
        'Keep the whole source collection and playlist tree in the
        output.'
        assert 'Keep the wh...able hand-off.' == 'Keep the wh...the output.'
    """
    descriptions = _artboard_text("opt-d")
    assert buildplaylist_view.ALLOW_UNMATCHED_NOTE in descriptions, (
        "the screen's description is not the artboard's: "
        f"{buildplaylist_view.ALLOW_UNMATCHED_NOTE!r}"
    )
    assert buildplaylist_view.FULL_COLLECTION_NOTE in descriptions, (
        "the screen's description is not the artboard's: "
        f"{buildplaylist_view.FULL_COLLECTION_NOTE!r}"
    )
    titles = _artboard_text("opt-t")
    assert buildplaylist_view.ALLOW_UNMATCHED_LABEL in titles
    assert buildplaylist_view.FULL_COLLECTION_LABEL in titles
    assert buildplaylist_view.REPORT_READ_ONLY_NOTE in _artboard_text("faint")


def test_the_option_row_and_its_two_notes_carry_the_artboards_values():
    """Specs.dc.html:47's .opt is a bordered row at 11px by 12px inside a
    6px radius on SURFACE_1, :49's .opt-t is 13px at 600, :50's .opt-d is
    12px of TEXT_MUTED at a 1.45 line-height, and :185's note is 11.5px
    of TEXT_FAINT 8px below the table. The description's indent is the
    switch's own track width plus the row's gap, because Quasar builds
    the label as the switch's child and the note is a sibling of the
    whole switch.

    Mutation: OPTION_NOTE_INDENT was set to '34px', the track's width
    with the row's gap dropped, and this guard rerun. Observed:
        AssertionError: OPTION_NOTE_INDENT is 34px, not the 34px track
        plus the 11px gap
        assert '34px' == '45px'
    """
    assert theme.OPTION_NOTE_INDENT == (
        f"{int(theme.SWITCH_TRACK_WIDTH.removesuffix('px')) + int(theme.SPACE_11.removesuffix('px'))}px"
    ), (
        f"OPTION_NOTE_INDENT is {theme.OPTION_NOTE_INDENT}, not the "
        f"{theme.SWITCH_TRACK_WIDTH} track plus the {theme.SPACE_11} gap"
    )
    sheet = theme.page_stylesheet()
    row = _rule(sheet, ".buildplaylist-option")
    assert f"border: 1px solid {theme.BORDER}" in row
    assert f"border-radius: {theme.RADIUS_LG}" in row
    assert f"background: {theme.SURFACE_1}" in row
    assert f"padding: {theme.SPACE_11} {theme.SPACE_12}" in row
    label = _rule(sheet, '[dir="ltr"] .buildplaylist-option .q-toggle__label')
    assert f"font-size: {theme.TYPE_13}" in label and "font-weight: 600" in label
    assert f"padding-left: {theme.SPACE_11}" in label
    note = _rule(sheet, ".buildplaylist-option-note")
    assert f"margin: {theme.SPACE_3} 0 0 {theme.OPTION_NOTE_INDENT}" in note
    assert f"font-size: {theme.TYPE_12}" in note
    assert f"color: {theme.TEXT_MUTED}" in note
    assert "line-height: 1.45" in note
    report_note = _rule(sheet, ".buildplaylist-report-note")
    assert f"margin: {theme.SPACE_8} 0 0" in report_note
    assert f"font-size: {theme.TYPE_11_5}" in report_note
    assert f"color: {theme.TEXT_FAINT}" in report_note


def _rule(sheet: str, selector: str) -> str:
    """Everything the sheet declares for one selector, as one block."""
    blocks = re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", sheet)
    assert blocks, f"the stylesheet emits no {selector} rule"
    return " ".join(blocks)


def _page_function() -> ast.FunctionDef:
    """_build_build_playlist_page, the function that builds the screen."""
    module = ast.parse(_APP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_build_playlist_page":
            return node
    raise AssertionError("app.py defines no _build_build_playlist_page")


def _option_rows() -> list[ast.With]:
    """Every `with ui.element("div").classes("buildplaylist-option"):`
    block the page enters."""
    rows = []
    for node in ast.walk(_page_function()):
        if not isinstance(node, ast.With):
            continue
        call = node.items[0].context_expr
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "classes"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value == "buildplaylist-option"
        ):
            rows.append(node)
    return rows


def test_the_page_builds_each_switch_in_a_row_with_its_own_description():
    """Each switch is built inside a buildplaylist-option row that also
    holds a buildplaylist-option-note label, and the two pair the label
    constant with the description constant of the same setting - a row
    holding a switch and the other switch's description would read as
    correct to a guard counting rows.

    Mutation: the ui.label carrying ALLOW_UNMATCHED_NOTE was removed
    from the first option row in app.py and this guard rerun. Observed:
        AssertionError: the option row for ALLOW_UNMATCHED_LABEL builds
        no buildplaylist-option-note
        assert 0 == 1
    """
    rows = _option_rows()
    assert len(rows) == 2, f"app.py builds {len(rows)} option rows, not two"
    paired = {}
    for row in rows:
        source = ast.unparse(row)
        switches = re.findall(r"ui\.switch\(\s*buildplaylist_view\.(\w+)", source)
        assert len(switches) == 1, f"an option row builds {len(switches)} switches"
        notes = re.findall(
            r"ui\.label\(buildplaylist_view\.(\w+)\)\.classes\('buildplaylist-option-note'\)",
            source,
        )
        assert len(notes) == 1, (
            f"the option row for {switches[0]} builds "
            f"{len(notes)} buildplaylist-option-note"
        )
        paired[switches[0]] = notes[0]
    assert paired == {
        "ALLOW_UNMATCHED_LABEL": "ALLOW_UNMATCHED_NOTE",
        "FULL_COLLECTION_LABEL": "FULL_COLLECTION_NOTE",
    }, f"the switches and descriptions are paired as {paired}"


def test_the_page_builds_the_read_only_note_after_the_report_table():
    """The note is built in the report card's body, after report_table
    rather than inside it, so the run that clears and refills the table
    does not clear the note away with the previous run's rows.

    Mutation: the ui.label carrying REPORT_READ_ONLY_NOTE was moved
    inside the `with report_table:` block in write_playlist and this
    guard rerun. Observed:
        AssertionError: the card body builds no read-only note after
        report_table
        assert 0 == 1
    """
    body = None
    for node in ast.walk(_page_function()):
        if isinstance(node, ast.With) and "report_table = ui.element" in ast.unparse(node):
            body = node
    assert body is not None, "the page builds no report_table"
    statements = [ast.unparse(node) for node in body.body]
    table_at = next(
        i for i, text in enumerate(statements) if text.startswith("report_table = ")
    )
    after = [
        text
        for text in statements[table_at + 1 :]
        if "REPORT_READ_ONLY_NOTE" in text and "buildplaylist-report-note" in text
    ]
    assert len(after) == 1, (
        "the card body builds no read-only note after report_table"
    )
