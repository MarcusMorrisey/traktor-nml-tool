"""Guards for the Write step's control-height and dialog-focus fixes
(app.py, the confirm dialog inside _build_write_step's render()):

- The "Write output" button and the dialog's "Write" button both carry
  wizard-control and no heading-size class - a heading token on a
  control was the defect measured on the served page as 66.31px
  against Specs' 32px control height (Results.dc.html's own write
  control, .btn-pri, carries the control type size, not a heading
  one). "Write output" also carries an explicit tabindex=0, so it
  matches its own .closest('[tabindex]:not([tabindex^="-"])') lookup
  inside quasar.umd.js's QDialog.handleHide - the branch that restores
  focus on a key-triggered hide, which a plain <button> with no
  explicit tabindex attribute never matches.
- The dialog is wired to Quasar's own 'hide' event to return focus to
  the button that opened it (Specs.dc.html, "Accessibility rules":
  dialogs "return focus to whatever opened them").

These are source-text guards, not behavioural ones: they confirm the
wiring exists in app.py's source, not that a browser actually clamps
the button to 32px or actually restores focus on hide. The control
height half is also checked against the emitted stylesheet in
tests/test_gui_theme.py's existing class-reaches-app.py and
size/colour-stacking guards, which is as far as a guard can go without
rendering the page - the coordinator's own re-served, re-measured page
is the remaining check for the actual pixel values and for the focus
return, which no source-text guard can observe at all. That check
matters here more than usual: Quasar's escape-key detection
(quasar.umd.js's private focus-escape module) keys off the legacy
evt.keyCode === 27, a property browsers are well known not to
populate reliably for a synthetically dispatched KeyboardEvent, so a
driver that cannot send a trusted Escape may not exercise the same
code path a real keypress does.
"""

from __future__ import annotations

import re
from pathlib import Path

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def _classes_after(source: str, anchor: str) -> str:
    """The literal string argument of the first .classes(...) call
    found after `anchor` in `source` - anchor is a literal snippet
    naming the element (e.g. the button's own ui.button(...) call), so
    this reads the classes app.py actually attaches to that specific
    element rather than to any .classes(...) call in the file."""
    start = source.index(anchor)
    match = re.search(r'\.classes\("([^"]*)"\)', source[start:start + 400])
    assert match, f"no .classes(...) call found near {anchor!r}"
    return match.group(1)


def test_write_output_button_carries_no_heading_class():
    """The Write step's own "Write output" button carries wizard-control
    and no wizard-heading-* token - Results.dc.html's .btn-pri (the
    write control) carries the control type size, never a heading
    size, which wizard-heading-xs was on the served page (measured
    66.31px against Specs' 32px)."""
    source = _APP_PY.read_text(encoding="utf-8")
    classes = _classes_after(source, '"Write output"')
    assert "wizard-control" in classes.split()
    assert not any(tok.startswith("wizard-heading") for tok in classes.split()), classes


def test_a_reintroduced_heading_class_on_write_output_is_caught():
    """Mutation: wizard-heading-xs is spliced back into a copy of the
    real "Write output" button's classes() literal, reproducing the
    defect test_write_output_button_carries_no_heading_class exists to
    catch. Observed: the same any(...) check that guard uses reports
    True for the mutated classes string, rather than False."""
    source = _APP_PY.read_text(encoding="utf-8")
    classes = _classes_after(source, '"Write output"')
    mutated = f"wizard-heading-xs {classes}"
    assert any(tok.startswith("wizard-heading") for tok in mutated.split())


def test_dialog_write_button_carries_wizard_control():
    """The confirm dialog's "Write" button carries wizard-control, the
    same class its sibling "Cancel" button already carries and already
    computes ~32px with (measured on the served page) - the dialog
    Write button previously carried no wizard class at all and
    computed 36px."""
    source = _APP_PY.read_text(encoding="utf-8")
    classes = _classes_after(source, 'ui.button("Write", on_click=lambda: (dialog.close(), _do_write())')
    assert "wizard-control" in classes.split()


def test_dialog_returns_focus_to_its_opener_on_hide():
    """app.py wires dialog.on("hide", ...) to call run_method("focus")
    on write_button - the button that opens the dialog
    (write_button.on_click(dialog.open)) - rather than on_click
    handlers on the individual Cancel/Write buttons, since Quasar's
    own 'hide' event fires once for every dismissal route (a button
    click, Escape, or a backdrop click) alike, per the coordinator's
    requirement that a fix depending on the close path work for
    Cancel and Escape both. This is a source-text check only: it
    cannot observe whether a browser actually moves focus on hide,
    which is not guardable without one."""
    source = _APP_PY.read_text(encoding="utf-8")
    match = re.search(r'dialog\.on\("hide",\s*lambda:\s*write_button\.run_method\("focus"\)\)', source)
    assert match, "dialog.on(\"hide\", ...) restoring focus to write_button was not found in app.py"


def test_a_removed_hide_binding_is_caught():
    """Mutation: the dialog.on("hide", ...) line is stripped from a
    copy of app.py's real source, reproducing the regression
    test_dialog_returns_focus_to_its_opener_on_hide exists to catch.
    Observed: the same regex search that guard uses finds no match
    against the stripped source."""
    source = _APP_PY.read_text(encoding="utf-8")
    stripped = source.replace(
        'dialog.on("hide", lambda: write_button.run_method("focus"))', ""
    )
    assert stripped != source, "expected dialog.on(...) line not found to strip"
    match = re.search(r'dialog\.on\("hide",\s*lambda:\s*write_button\.run_method\("focus"\)\)', stripped)
    assert match is None


def test_write_output_button_carries_tabindex_zero():
    """"Write output" carries props("... tabindex=0 ..."), so
    quasar.umd.js's QDialog.handleHide can find this exact element via
    .closest('[tabindex]:not([tabindex^="-"])') on a key-triggered
    hide, the same way it already reaches it directly on a
    non-key-triggered one - a plain <button> carries no tabindex
    attribute by default, so that lookup finds nothing without this."""
    source = _APP_PY.read_text(encoding="utf-8")
    start = source.index('"Write output"')
    props_match = re.search(r'\.props\("([^"]*)"\)', source[start:start + 400])
    assert props_match, "no .props(...) call found near \"Write output\""
    assert "tabindex=0" in props_match.group(1).split()


def test_a_removed_tabindex_is_caught():
    """Mutation: tabindex=0 is stripped from a copy of the real
    "Write output" button's props() literal, reproducing the
    regression test_write_output_button_carries_tabindex_zero exists
    to catch. Observed: the same membership check that guard uses
    reports False against the mutated props string."""
    source = _APP_PY.read_text(encoding="utf-8")
    start = source.index('"Write output"')
    props_match = re.search(r'\.props\("([^"]*)"\)', source[start:start + 400])
    mutated = props_match.group(1).replace("tabindex=0", "").split()
    assert "tabindex=0" not in mutated


def test_refusal_label_carries_no_tint_and_starts_invisible():
    """refusal_label's own .classes(...) call carries no
    wizard-tag-review - it is added only in refresh_refusal's reason
    branch - and the label starts invisible via set_visibility(False)
    right after creation, so an empty label reserves neither a tinted
    box (wizard-tag-review paints a background and border even with no
    text) nor its own line under the reconnect count."""
    source = _APP_PY.read_text(encoding="utf-8")
    start = source.index("refusal_label = ui.label()")
    window = source[start:start + 300]
    classes_match = re.search(r'\.classes\("([^"]*)"\)', window)
    assert classes_match is not None
    assert "wizard-tag-review" not in classes_match.group(1).split()
    assert "refusal_label.set_visibility(False)" in window


def test_refresh_refusal_toggles_the_tint_and_visibility_together():
    """refresh_refusal's reason branch adds wizard-tag-review and shows
    the label; its no-reason branch removes wizard-tag-review and
    hides it again - the tint and the visibility change together,
    rather than the tint staying attached with only the text cleared,
    which is the defect (a stray tinted box under the reconnect count)
    this guard exists to catch."""
    source = _APP_PY.read_text(encoding="utf-8")
    start = source.index("def refresh_refusal() -> None:")
    end = source.index("refresh_refusal()", start + len("def refresh_refusal() -> None:"))
    body = source[start:end]
    assert 'refusal_label.classes(add="wizard-tag-review")' in body
    assert "refusal_label.set_visibility(True)" in body
    assert 'refusal_label.classes(remove="wizard-tag-review")' in body
    assert "refusal_label.set_visibility(False)" in body


def test_a_removed_visibility_toggle_is_caught():
    """Mutation: the no-reason branch's
    'refusal_label.set_visibility(False)' line is stripped from a copy
    of app.py's real refresh_refusal source, standing in for the stray
    tinted box regression this guard exists to catch - the tint
    removed but the box still reserving its line, or (if the add-tint
    line were the one dropped instead) the box still painted with
    empty text. Observed: the same substring check
    test_refresh_refusal_toggles_the_tint_and_visibility_together uses
    finds 'refusal_label.set_visibility(False)' present only once
    (the initial one, outside refresh_refusal) rather than the two
    real source carries."""
    source = _APP_PY.read_text(encoding="utf-8")
    start = source.index("def refresh_refusal() -> None:")
    end = source.index("refresh_refusal()", start + len("def refresh_refusal() -> None:"))
    body = source[start:end]
    mutated_body = body.replace(
        "                        refusal_label.set_visibility(False)\n", "", 1,
    )
    assert mutated_body != body, "fixture assumption stale: visibility(False) line not found in refresh_refusal"
    assert "refusal_label.set_visibility(False)" not in mutated_body
