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
