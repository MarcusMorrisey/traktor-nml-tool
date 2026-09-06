"""Guards the shell rules theme.py emits, read as source text under the
system interpreter, which has no nicegui.

What a guard here asserts is a rule's presence and content. What it
cannot assert is that the browser gave the layout the viewport:
theme.FONT_SANS named IBM Plex throughout the period the page painted
Segoe UI, so a guard that reads a name is true in exactly the broken
state. The rendered height and the scroll owner belong to the
served-page record (DL-189).

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
    theme.py's source, so a constant renamed or a value interpolated
    from somewhere else is still read as the sheet emits it. Every
    matching rule is joined rather than only the first, because a
    selector the sheet names twice - .q-page carries its ground in one
    rule and its height in another - declares the union of the two.
    """
    blocks = re.findall(
        re.escape(selector) + r"\s*\{([^}]*)\}", theme.page_stylesheet()
    )
    assert blocks, f"the stylesheet emits no {selector} rule"
    return "".join(blocks)


def test_each_band_rule_carries_its_band_height():
    """The header band measures at HEADER_BAND_HEIGHT and the footer band
    at FOOTER_BAND_HEIGHT, the two fixed rows Main.dc.html:15 draws.

    Mutation: the `height: {HEADER_BAND_HEIGHT}; ` declaration was
    deleted from the .wizard-header-band rule in page_stylesheet() and
    this guard rerun. Observed:
        E       AssertionError: .wizard-header-band declares no height
        E       assert 'height: 56px' in ' align-items: center; justify-content: space-between; gap: 24px; padding: 0 24px; background: #17191C; border-bottom: 1px solid #2A2E32; '
        E        +  where ' align-items: center; justify-content: space-between; gap: 24px; padding: 0 24px; background: #17191C; border-bottom: 1px solid #2A2E32; ' = _rule('.wizard-header-band')
    """
    assert f"height: {theme.HEADER_BAND_HEIGHT}" in _rule(".wizard-header-band"), (
        ".wizard-header-band declares no height"
    )
    assert f"height: {theme.FOOTER_BAND_HEIGHT}" in _rule(".wizard-footer-band"), (
        ".wizard-footer-band declares no height"
    )


def test_each_band_restates_the_alignment_and_padding_the_framework_sets():
    """The block at nicegui.css lines 14-28 sets display: flex,
    flex-direction: column, align-items: flex-start, gap:
    var(--nicegui-default-gap) and padding: var(--nicegui-default-padding)
    on a selector list that includes .nicegui-header and .nicegui-footer -
    the elements ui.header and ui.footer build - and the block at lines
    41-46 then overrides those two selectors to flex-direction: row. So
    the alignment and the padding are what survive for a band to restate,
    and the row direction is already the framework's own; a band rule
    restating it would be redundant with the sheet it sits after
    (DL-192).

    Mutation: `align-items: center; ` was deleted from the
    .wizard-footer-band rule and this guard rerun. Observed:
        E           AssertionError: .wizard-footer-band does not restate the alignment the framework sets to flex-start
        E           assert 'align-items: center' in ' justify-content: space-between; gap: 24px; padding: 0 24px; height: 64px; background: #17191C; border-top: 1px solid #2A2E32; '

    Mutation: `flex-direction: row; ` was planted at the head of the
    .wizard-header-band rule and this guard rerun. Observed:
        E           AssertionError: .wizard-header-band restates flex-direction, which nicegui.css already sets to row for this element
        E           assert 'flex-direction' not in ' flex-direc...id #2A2E32; '
        E
        E             'flex-direction' is contained here:
        E                flex-direction: row; align-items: center; justify-content: space-between; gap: 24px; padding: 0 24px; height: 56px; background: #17191C; border-bottom: 1px solid #2A2E32;
        E             ?  ++++++++++++++
    """
    for selector in (".wizard-header-band", ".wizard-footer-band"):
        block = _rule(selector)
        assert "align-items: center" in block, (
            f"{selector} does not restate the alignment the framework sets "
            "to flex-start"
        )
        assert f"padding: 0 {theme.SPACE_24}" in block, (
            f"{selector} does not restate the padding the framework sets to 1rem"
        )
        assert "flex-direction" not in block, (
            f"{selector} restates flex-direction, which nicegui.css already "
            "sets to row for this element"
        )


def test_the_middle_owns_the_scroll_and_every_parent_bounds_its_height():
    """nicegui's client.py:110-113 builds q-layout > q-page-container >
    q-page > div.nicegui-content, and Quasar's own sheet gives that chain
    no height, so the middle can scroll rather than grow only if every
    element between the viewport and it carries a bounded height. app.py
    constructs none of those four elements, which is why the height rules
    key on the framework's own class names (DL-193).

    Mutation: the `.q-page {{ height: 100%; }}` line was deleted from
    page_stylesheet(), leaving q-page with only the ground rule the
    sheet already carried for it and no bound between the page container
    and the content, and this guard rerun. Observed:
        E       AssertionError: assert 'height: 100%' in ' background: #0F1113; color: #E8EBED; '
        E        +  where ' background: #0F1113; color: #E8EBED; ' = _rule('.q-page')
    """
    middle = _rule(".wizard-middle")
    assert "overflow-y: auto" in middle, (
        ".wizard-middle declares no overflow-y, so the document is the scroll owner"
    )
    assert "min-height: 0" in middle
    assert "height: 100vh" in _rule(".q-layout")
    page_container = _rule(".q-page-container")
    assert "height: 100vh" in page_container
    # QLayout writes each band's height onto this element as inline
    # padding, so the middle is left the right space only under
    # border-box.
    assert "box-sizing: border-box" in page_container
    assert "height: 100%" in _rule(".q-page")
    content = _rule(".nicegui-content")
    assert "height: 100%" in content
    assert "min-height: 0" in content


def test_no_shell_or_card_rule_declares_a_width():
    """.wizard-content-width stays the single width owner, so no band,
    middle, footer or card rule declares a width of its own.

    Mutation: `max-width: {CONTENT_WIDTH}; ` was planted at the end of
    the .wizard-middle rule and this guard rerun. Observed:
        E           AssertionError: .wizard-middle declares a width, so .wizard-content-width is not the only width owner
        E           assert 'width' not in ' flex: 1 1 ...dth: 64rem; '
        E
        E             'width' is contained here:
        E               lumn; max-width: 64rem;
        E             ?           +++++
    """
    for selector in (
        ".wizard-header-band",
        ".wizard-footer-band",
        ".wizard-middle",
        ".wizard-footer-note",
        ".wizard-footer-actions",
        ".wizard-card",
        ".wizard-card-head",
        ".wizard-card-title",
        ".wizard-card-body",
    ):
        assert "width" not in _rule(selector), (
            f"{selector} declares a width, so .wizard-content-width is not "
            "the only width owner"
        )


def test_the_middle_counters_the_alignment_its_parent_sets():
    """The middle fills its parent's width, so the centred column centres
    inside the page rather than inside a shrunken box.

    nicegui.css lines 14-28 set display: flex, flex-direction: column
    and align-items: flex-start on a selector list that includes
    .nicegui-content, the element nicegui's client.py builds as the
    middle's parent, and the override at lines 41-46 reaches only
    .nicegui-header and .nicegui-footer. Under align-items: flex-start a
    flex child takes its content's width on the cross axis, so the
    middle needs its own cross-axis declaration. align-self: stretch is
    that declaration and not a width, which leaves
    .wizard-content-width the sheet's one width owner and keeps this
    rule clear of
    test_no_shell_or_card_rule_declares_a_width (DL-193).

    Mutation: `align-self: stretch; ` was deleted from the
    .wizard-middle rule in page_stylesheet() and this guard rerun.
    Observed:
        E       AssertionError: .wizard-middle declares no align-self, so its parent's align-items: flex-start shrinks it to its content's width
        E       assert 'align-self: stretch' in ' flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 22px 24px 6px; gap: 20px; display: flex; flex-direction: column; '
        E        +  where ' flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 22px 24px 6px; gap: 20px; display: flex; flex-direction: column; ' = _rule('.wizard-middle')
    """
    assert "align-self: stretch" in _rule(".wizard-middle"), (
        ".wizard-middle declares no align-self, so its parent's "
        "align-items: flex-start shrinks it to its content's width"
    )
