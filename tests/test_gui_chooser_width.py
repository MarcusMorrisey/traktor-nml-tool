"""Guards that every chooser button in the GUI is sized to its label
rather than stretched across the column it stands in (DL-299).

The artboards draw each "Choose ..." control and the CSV template
control as a .btn in a .row beside what it acts on
(design/reconnect-wizard/Main.dc.html:92-97,
design/build-playlist/Specs.dc.html:42). A Quasar button standing as a
direct child of a flex column takes the column's width, because the
column's default align-items stretches it, which is how /reconnect's
two choosers measured 908px wide around labels under 150px.

A guard reading the row rule alone is green while no call site sits in
the row (DL-189), so this reads app.py: the element each chooser's
`ui.button(` call is built inside must carry a class the stylesheet
declares as a flex row. app.py imports nicegui, which the system
interpreter running this suite does not have, so it is read as an AST
and never imported. The widths themselves are read on the served page
in docs/2026-09-16-chooser-width-browser-record.md (DL-084, DL-169).

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from traktor_nml.gui import theme

REPO_ROOT = Path(__file__).resolve().parents[1]
_APP_PY = REPO_ROOT / "traktor_nml" / "gui" / "app.py"

_CHOOSER_LABEL = re.compile(r"^(Choose\b|Download CSV template$)")


def _rule_body(sheet: str, cls: str) -> str | None:
    match = re.search(r"(?m)^\." + re.escape(cls) + r"\s*\{([^}]*)\}", sheet)
    return match.group(1) if match else None


def _is_flex_row(sheet: str, cls: str) -> bool:
    body = _rule_body(sheet, cls)
    if body is None:
        return False
    return (
        re.search(r"display:\s*flex\b", body) is not None
        and re.search(r"flex-direction:\s*column", body) is None
    )


def _classes_of(expr: ast.expr) -> list[str]:
    """The classes a `ui.element(...).classes("...")` chain names."""
    found: list[str] = []
    node = expr
    while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "classes":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.extend(arg.value.split())
        node = node.func.value
    return found


def _choosers_and_containers() -> list[tuple[str, int, list[str]]]:
    tree = ast.parse(_APP_PY.read_text(encoding="utf-8"))
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    rows: list[tuple[str, int, list[str]]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "button"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "ui"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and _CHOOSER_LABEL.match(node.args[0].value)
        ):
            continue
        up = parents.get(node)
        while up is not None and not isinstance(up, ast.With):
            up = parents.get(up)
        container = _classes_of(up.items[0].context_expr) if up is not None else []
        rows.append((node.args[0].value, node.lineno, container))
    return rows


def test_every_chooser_is_found():
    """The walk reaches the call sites it is meant to guard, so an empty
    reading cannot pass the guard below by finding nothing.

    Mutation: `_CHOOSER_LABEL` changed to `re.compile(r"^Pick\\b")`.
    Observed:
        E       assert 0 >= 10
        E        +  where 0 = len([])
        E        +    where [] = _choosers_and_containers()
    """
    assert len(_choosers_and_containers()) >= 10


def test_every_chooser_stands_in_a_flex_row_the_sheet_declares():
    """Mutation: the "Choose collection file..." call site in app.py
    dedented by four spaces, out of its wizard-path-row and back into
    the card body's column, with app.py copied aside beforehand and
    restored from the copy. Observed:
        E       AssertionError: chooser buttons outside a flex row: [('Choose collection file...', 428, ['wizard-card-body'])]
        E       assert [('Choose col...-card-body'])] == []
        E
        E         Left contains one more item: ('Choose collection file...', 428, ['wizard-card-body'])
        E         Use -v to get more diff
    """
    sheet = theme.page_stylesheet()
    stretched = [
        (label, line, container)
        for label, line, container in _choosers_and_containers()
        if not any(_is_flex_row(sheet, cls) for cls in container)
    ]
    assert stretched == [], f"chooser buttons outside a flex row: {stretched}"


# The rows that stand a path beside the control choosing it. A flex row
# centres each item's margin box, so .wizard-control's bottom margin on
# a button in one of these rows lifts it above its path (DL-301).
_CHOOSER_ROWS = ("wizard-path-row", "wizard-field-row", "buildplaylist-input-row")
# "Choose collection file...", "Choose folder..." and the like: a control
# that picks a path. The conflict table's bare "Choose..." picks a
# candidate, not a path, and stands in no path row.
_PATH_CHOOSER_LABEL = re.compile(r"^Choose .*(file|folder)\.\.\.$")


def _button_classes(tree: ast.AST, lineno: int, label: str) -> list[str]:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "classes"
        ):
            inner = node.func.value
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "button"
                and inner.lineno == lineno
                and inner.args
                and isinstance(inner.args[0], ast.Constant)
                and inner.args[0].value == label
            ):
                return _classes_of(node)
    return []


def _zero_bottom_margin_in(sheet: str, row_cls: str) -> bool:
    """A rule whose selector list names `.row_cls > .wizard-control`
    and whose body sets margin-bottom to zero."""
    child = re.escape(f".{row_cls} > .wizard-control")
    for match in re.finditer(r"(?m)^([^{}\n]*)\{([^}]*)\}", sheet):
        selectors = [s.strip() for s in match.group(1).split(",")]
        if any(re.fullmatch(child, s) for s in selectors) and re.search(
            r"margin-bottom:\s*0(px)?\s*;", match.group(2)
        ):
            return True
    return False


def test_every_path_chooser_stands_in_a_chooser_row():
    """The margin rule below reaches the page only through these rows, so
    each path chooser must be built in one and carry .wizard-control.

    Mutation: `_CHOOSER_ROWS` reduced to `("wizard-path-row",
    "wizard-field-row")`. Observed:
        E       AssertionError: path choosers outside a chooser row: [('Choose file...', 1823, ['buildplaylist-input-row'], ['wizard-control', 'wizard-control-fill']), ('Choose file...', 1849, ['buildplaylist-input-row'], ['wizard-control', 'wizard-control-fill']), ('Choose folder...', 1852, ['buildplaylist-input-row'], ['wizard-control', 'wizard-control-fill']), ('Choose folder...', 1890, ['buildplaylist-input-row'], ['wizard-control', 'wizard-control-fill'])]
        E       assert [('Choose fil...ntrol-fill'])] == []
        E
        E         Left contains 4 more items, first extra item: ('Choose file...', 1823, ['buildplaylist-input-row'], ['wizard-control', 'wizard-control-fill'])
        E         Use -v to get more diff
    """
    tree = ast.parse(_APP_PY.read_text(encoding="utf-8"))
    found = [
        (label, line, container, _button_classes(tree, line, label))
        for label, line, container in _choosers_and_containers()
        if _PATH_CHOOSER_LABEL.match(label)
    ]
    assert len(found) >= 8
    outside = [
        row
        for row in found
        if not any(cls in _CHOOSER_ROWS for cls in row[2])
        or "wizard-control" not in row[3]
    ]
    assert outside == [], f"path choosers outside a chooser row: {outside}"


def test_every_chooser_row_cancels_the_control_bottom_margin():
    """Mutation: the `.wizard-path-row > .wizard-control, ...
    { margin-bottom: 0; }` rule and its comment removed from theme.py,
    with theme.py copied aside beforehand and restored from the copy.
    Observed:
        E       AssertionError: chooser rows whose .wizard-control keeps its bottom margin: ['wizard-path-row', 'wizard-field-row', 'buildplaylist-input-row']
        E       assert ['wizard-path...st-input-row'] == []
        E
        E         Left contains 3 more items, first extra item: 'wizard-path-row'
        E         Use -v to get more diff
    """
    sheet = theme.page_stylesheet()
    for cls in _CHOOSER_ROWS:
        assert _is_flex_row(sheet, cls), cls
        assert "align-items: center" in (_rule_body(sheet, cls) or ""), cls
    missing = [cls for cls in _CHOOSER_ROWS if not _zero_bottom_margin_in(sheet, cls)]
    assert missing == [], f"chooser rows whose .wizard-control keeps its bottom margin: {missing}"
