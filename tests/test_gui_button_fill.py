"""Guards that every button in the GUI is drawn on the action blue with
the ground as its ink, apart from the four kinds named below (DL-273).

The call-site guard reads app.py rather than theme.py. A guard reading
the stylesheet's fill rule passes while every button still renders grey,
because a rule no call site names paints nothing - the state DL-273
corrects - so the discriminating reading is which class each
`ui.button(` call carries (DL-189). app.py imports nicegui, which the
system interpreter running this suite does not have, so it is read as an
AST and never imported.

What the browser computes for these classes is read on the served page
in docs/2026-09-16-button-fill-browser-record.md (DL-084, DL-169).

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
_DESIGN = REPO_ROOT / "design"

# The two classes that paint a button's fill: the primary action's own
# rule, and the rule every other neutral button carries.
_FILL_CLASSES = ("wizard-control-fill", "wizard-control-primary")

# The buttons that keep their own colour, keyed by the class that
# carries it. Each would lose what it says if it were painted blue.
_EXEMPT = {
    # Review.dc.html:37's .btn-ok: accepting a match is drawn in the
    # found hue, the colour the row turns once it is accepted.
    "wizard-decision-accept": "Accept",
    # Review.dc.html:38's .btn-no: rejecting is drawn in the not-found
    # hue, the colour of what the row becomes.
    "wizard-tag-missing": "Reject",
    # The Review step's filter chips, under both classes a chip can
    # carry: the tinted chip is the active filter and the outlined ones
    # are not, so one fill on all of them would hide which filter is
    # applied.
    "wizard-tag-action": "the active filter chip",
    "wizard-tag-action-outline": "the inactive filter chips",
    # Resolve.dc.html's .cand: an answer is a record the operator reads
    # field by field, a button only so the whole card is the target.
    "wizard-answer-fields": "the answer card",
}


def _is_ui_button(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "button"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "ui"
    )


def _string_options(node: ast.AST) -> list:
    """Every class string a classes() argument can be at run time."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _string_options(node.body) + _string_options(node.orelse)
    return []


def _button_sites(source: str) -> list:
    """(line, class strings) for every ui.button( call in source.

    A button's classes are the argument of the .classes() call its
    constructor chain ends in, through any .props() between the two. A
    button with no .classes() call at all is listed with no strings, so
    it fails the guard rather than escaping it."""
    module = ast.parse(source)
    classes_by_button = {}
    for node in ast.walk(module):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "classes"
            and len(node.args) == 1
        ):
            continue
        inner = node.func.value
        while (
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Attribute)
            and inner.func.attr == "props"
        ):
            inner = inner.func.value
        if _is_ui_button(inner):
            classes_by_button[id(inner)] = _string_options(node.args[0])
    return sorted(
        (node.lineno, classes_by_button.get(id(node), []))
        for node in ast.walk(module)
        if _is_ui_button(node)
    )


def _unfilled(source: str) -> list:
    """The call sites that carry neither a fill class nor an exempting
    class on every branch of their class string."""
    missing = []
    for line, options in _button_sites(source):
        tokens = [set(option.split()) for option in options]
        if not tokens:
            missing.append(line)
            continue
        for option in tokens:
            if not option & set(_FILL_CLASSES) and not option & set(_EXEMPT):
                missing.append(line)
                break
    return missing


def test_every_button_carries_a_fill_or_is_a_named_exemption():
    """Every `ui.button(` call in app.py carries wizard-control-fill or
    wizard-control-primary, or one of the classes _EXEMPT names.

    Mutation: ` wizard-control-fill` deleted from the "Choose track
    list..." call's classes string. Observed:
        E       AssertionError: ui.button( call sites painted neither blue nor exempt, by line: [1799]
        E       assert [1799] == []
        E
        E         Left contains one more item: 1799
        E         Use -v to get more diff
    """
    missing = _unfilled(_APP_PY.read_text(encoding="utf-8"))
    assert missing == [], (
        f"ui.button( call sites painted neither blue nor exempt, by line: {missing}"
    )


def test_every_exemption_names_a_button_that_exists_and_is_not_filled():
    """Each exempting class stands on at least one button and on no
    button that is also filled, so an exemption cannot outlive the
    button it was written for or sit on a button painted blue anyway.

    Mutation: "wizard-decision-accept" in the Accept call's class
    string renamed to "wizard-decision-accepted". Observed:
        E       AssertionError: exemptions with no button, or on a filled one: ['wizard-decision-accept']
        E       assert ['wizard-decision-accept'] == []
        E
        E         Left contains one more item: 'wizard-decision-accept'
        E         Use -v to get more diff
    """
    sites = _button_sites(_APP_PY.read_text(encoding="utf-8"))
    stale = []
    for exempt in _EXEMPT:
        carriers = [
            set(option.split())
            for _, options in sites
            for option in options
            if exempt in option.split()
        ]
        if not carriers or any(tokens & set(_FILL_CLASSES) for tokens in carriers):
            stale.append(exempt)
    assert stale == [], f"exemptions with no button, or on a filled one: {stale}"


_SHEET_RULE = re.compile(r"([^{}]+)\{([^}]*)\}")


def _rule(selector: str) -> str:
    """The body of the stylesheet rule whose selector is exactly this."""
    sheet = re.sub(r"/\*.*?\*/", "", theme.page_stylesheet(), flags=re.DOTALL)
    for found, body in _SHEET_RULE.findall(sheet):
        if found.strip() == selector:
            return body
    raise AssertionError(f"no rule for {selector} in page_stylesheet()")


def test_the_fill_rule_paints_action_with_ground_ink():
    """The fill carries ACTION as its ground and GROUND as its ink - the
    pair the primary action already carries - at the design's .btn
    weight of 500, below the primary's 600. It carries no border: a 1px
    border measured the control 34px tall against Specs' 32px.

    Mutation: `color: {GROUND}` in theme.py's .wizard-control-fill rule
    replaced by `color: {TEXT}`. Observed:
        E       AssertionError: assert 'color: #0F1113' in ' background: #56B4E9; color: #E8EBED; font-weight: 500; '
    """
    body = _rule(".wizard-control-fill")
    assert f"background: {theme.ACTION}" in body
    assert "border" not in body
    assert f"color: {theme.GROUND}" in body
    assert "font-weight: 500" in body
    assert "font-weight: 600" in _rule(".wizard-control-primary")


def test_the_ink_on_the_fill_clears_the_text_floor():
    """GROUND on ACTION clears Specs' 4.5:1, computed with the WCAG
    relative-luminance formula from theme.py's own constants.

    Mutation: the pair computed with TEXT in place of GROUND - the
    light ink every grey button carries. Observed:
        E       AssertionError: #E8EBED on #56B4E9 reaches only 1.93:1
        E       assert 1.9270089955942784 >= 4.5
    """
    def luminance(hex_colour: str) -> float:
        channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            for c in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    ink, fill = theme.GROUND, theme.ACTION
    lighter, darker = sorted((luminance(ink), luminance(fill)), reverse=True)
    ratio = (lighter + 0.05) / (darker + 0.05)
    assert ratio >= 4.5, f"{ink} on {fill} reaches only {ratio:.2f}:1"


def test_a_disabled_blue_button_takes_the_off_colours():
    """A disabled filled or primary button is drawn with .btn.off's
    ground, border and ink, so it does not read as a blue control
    waiting to be pressed. Quasar marks a disabled q-btn with the
    `disabled` class; the served page reads which class it carries.

    Mutation: the `.wizard-control-fill.disabled` rule deleted from
    theme.py. Observed:
        E       AssertionError: no rule for .wizard-control-fill.disabled in page_stylesheet()
    """
    for selector in (".wizard-control-fill.disabled", ".wizard-control-primary.disabled"):
        body = _rule(selector)
        assert f"background: {theme.BORDER_SUBTLE_3}" in body, selector
        assert f"box-shadow: inset 0 0 0 {theme.SPACE_1} {theme.BORDER}" in body, selector
        assert f"color: {theme.TEXT_SUBTLE_3}" in body, selector


def test_no_button_label_is_forced_to_uppercase():
    """.wizard-control, which every button carries, sets its label in
    the case it is written in. Quasar's q-btn uppercases its label and
    sits in a layer, so this unlayered rule is the one that paints.

    Mutation: `text-transform: none; ` deleted from theme.py's
    .wizard-control rule. Observed:
        E       AssertionError: assert 'text-transform: none' in ' min-height: 32px; margin-bottom: 8px; white-space: nowrap; '
        E        +  where ' min-height: 32px; margin-bottom: 8px; white-space: nowrap; ' = _rule('.wizard-control')
    """
    assert "text-transform: none" in _rule(".wizard-control")


_BTN_RULE = re.compile(r"(?m)^\s*\.btn\{([^}]*)\}")


def test_every_artboard_draws_its_buttons_blue():
    """Every artboard's own .btn rule draws the action blue with the
    ground as ink, so the design set and the page agree (DL-071).

    Mutation: design/build-playlist/Specs.dc.html's .btn rule set back
    to `border:1px solid #3C4248;background:#22262A;color:#E8EBED`.
    Observed:
        E       AssertionError: artboards whose .btn is not the action blue: ['build-playlist/Specs.dc.html']
        E       assert ['build-playl...pecs.dc.html'] == []
        E
        E         Left contains one more item: 'build-playlist/Specs.dc.html'
        E         Use -v to get more diff
    """
    grey = []
    artboards = sorted(_DESIGN.glob("*/*.dc.html"))
    assert artboards, "no artboards found under design/"
    for artboard in artboards:
        for body in _BTN_RULE.findall(artboard.read_text(encoding="utf-8")):
            if not (
                "background:#56B4E9" in body
                and "border:1px solid #56B4E9" in body
                and "color:#0F1113" in body
            ):
                grey.append(artboard.relative_to(_DESIGN).as_posix())
    assert grey == [], f"artboards whose .btn is not the action blue: {grey}"
