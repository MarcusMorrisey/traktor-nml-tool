"""Guards the card triplet: the four rules theme.py emits for
Main.dc.html:32-35's .card, .card-h, .card-t and .card-b.

What the browser laid out - the computed padding, the border, the radius
- belongs to the served-page record (DL-189); what these guards hold is
each rule's content. That the four class names reach app.py is already
swept by tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py,
so no guard here repeats it; what that sweep cannot see is a rule the
sheet keeps emitting with no call site left, which the last guard holds.
"""

from __future__ import annotations

import re
from pathlib import Path

from traktor_nml.gui import theme

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"
# app.py is read as text here for one reason only: the last guard holds
# that no call site names the single-box class, which is a direction the
# class-reach sweep in tests/test_gui_theme.py does not walk (DL-196).


def _rule(selector: str) -> str:
    """Everything the sheet declares for one selector, as one block, read
    out of the sheet page_stylesheet() emits rather than out of theme.py's
    source."""
    blocks = re.findall(
        re.escape(selector) + r"\s*\{([^}]*)\}", theme.page_stylesheet()
    )
    assert blocks, f"the stylesheet emits no {selector} rule"
    return "".join(blocks)


def test_the_card_box_carries_the_ground_border_and_radius():
    """Main.dc.html:32's .card.

    Mutation: RADIUS_XL was replaced by RADIUS_LG in the .wizard-card
    rule and this guard rerun. Observed:
        E       assert 'border-radius: 8px' in ' background: #17191C; border: 1px solid #2A2E32; border-radius: 6px; '
    """
    block = _rule(".wizard-card")
    assert f"background: {theme.SURFACE_2}" in block
    assert f"border: 1px solid {theme.BORDER}" in block
    assert f"border-radius: {theme.RADIUS_XL}" in block


def test_the_card_head_carries_its_padding_and_its_rule():
    """Main.dc.html:33's .card-h.

    Mutation: the `border-bottom: 1px solid {BORDER}; ` declaration was
    deleted from the .wizard-card-head rule and this guard rerun.
    Observed:
        E       assert 'border-bottom: 1px solid #2A2E32' in ' display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 15px; '
    """
    block = _rule(".wizard-card-head")
    assert f"padding: {theme.SPACE_11} {theme.SPACE_15}" in block
    assert f"border-bottom: 1px solid {theme.BORDER}" in block


def test_the_card_title_carries_its_weight_size_and_no_margin():
    """Main.dc.html:34's .card-t.

    Mutation: `margin: 0; ` was deleted from the .wizard-card-title rule
    and this guard rerun. Observed:
        E       assert 'margin: 0' in ' font-weight: 600; font-size: 13px; '
    """
    block = _rule(".wizard-card-title")
    assert "font-weight: 600" in block
    assert f"font-size: {theme.TYPE_13}" in block
    assert "margin: 0" in block


def test_the_card_body_carries_its_padding_and_column_gap():
    """Main.dc.html:35's .card-b.

    Mutation: SPACE_12 was replaced by SPACE_8 in the .wizard-card-body
    gap and this guard rerun. Observed:
        E       assert 'gap: 12px' in ' padding: 15px; display: flex; flex-direction: column; gap: 8px; '
    """
    block = _rule(".wizard-card-body")
    assert f"padding: {theme.SPACE_15}" in block
    assert "flex-direction: column" in block
    assert f"gap: {theme.SPACE_12}" in block


def test_no_single_box_rule_survives_beside_the_triplet():
    """Every section carries the triplet, so the single-box rule the
    triplet replaces has no call site and is not emitted (DL-196). This
    is the direction test_every_wizard_class_reaches_app_py cannot hold:
    that sweep reads the sheet for classes app.py lacks rather than the
    reverse.

    Mutation: the line
    `.wizard-surface {{ background: {SURFACE_2}; border: 1px solid
    {BORDER}; border-radius: {RADIUS_XL}; }}` was restored to
    page_stylesheet(), immediately above the .wizard-card rule, and this
    guard rerun. Observed:
        E       AssertionError: the stylesheet emits a .wizard-surface rule no call site names
        E       assert '.wizard-surface' not in '\\n@font-fac...x: none; }\\n'
        E
        E         '.wizard-surface' is contained here:
        E           -189). */
        E           .wizard-surface { background: #17191C; border: 1px solid #2A2E32; border-radius: 8px; }
        E         ? +++++++++++++++
        E           .wizard-card { background: #17191C; border: 1px solid #2A2E32; border-radius: 8px; }
        E           .wizard-card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 15px; border-bottom: 1px solid #2A2E32; }...
        E
        E         ...Full output truncated (163 lines hidden), use '-vv' to show
    """
    assert ".wizard-surface" not in theme.page_stylesheet(), (
        "the stylesheet emits a .wizard-surface rule no call site names"
    )
    assert "wizard-surface" not in _APP_PY.read_text(encoding="utf-8")
