"""Guards for the Review row's decision controls (app.py's
render_table), matching Review.dc.html's own .dec/.decd groups rather
than the three single-letter, action-blue buttons the row used to
carry:

- Accept/Reject/Undo render as words, not initials
  (Review.dc.html:156).
- Accept and Reject carry their own outcome tint
  (Review.dc.html:37-38's .btn-ok/.btn-no, reached here as the
  existing wizard-decision-accept/wizard-tag-missing status tokens),
  not Quasar's action-blue color=primary, which Specs reserves for the
  step's one primary action.
- A row that already carries a decision renders Review.dc.html:148's
  single, untinted "Undo" control instead of the Accept/Reject pair.

These are source-text guards: they confirm app.py's source carries the
right labels, classes and branch, not that a browser renders them at
any particular pixel value.
"""

from __future__ import annotations

from pathlib import Path

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def test_decision_buttons_use_words_not_initials():
    """The review row's decision controls render Accept/Reject/Undo as
    words, not single-letter initials - Review.dc.html:156 renders
    "Accept"/"Reject", and a screen reader has only "A button"/"R
    button" to announce otherwise (Specs.dc.html, "Accessibility
    rules")."""
    source = _APP_PY.read_text(encoding="utf-8")
    assert 'ui.button("Accept"' in source
    assert 'ui.button("Reject"' in source
    assert 'ui.button("Undo"' in source
    assert 'ui.button("A",' not in source
    assert 'ui.button("R",' not in source
    assert 'ui.button("U",' not in source


def test_an_initials_regression_is_caught():
    """Mutation: a copy of app.py's real source has
    'ui.button("Accept"' replaced with 'ui.button("A",' - the exact
    regression this guard exists to catch. Observed: the same
    membership checks test_decision_buttons_use_words_not_initials
    uses report 'ui.button("Accept"' absent and 'ui.button("A",'
    present in the mutated copy."""
    source = _APP_PY.read_text(encoding="utf-8")
    mutated = source.replace('ui.button("Accept"', 'ui.button("A",', 1)
    assert mutated != source, "fixture assumption stale: 'ui.button(\"Accept\"' not found"
    assert 'ui.button("Accept"' not in mutated
    assert 'ui.button("A",' in mutated


def _call_site(source: str, anchor: str, span: int = 300) -> str:
    start = source.index(anchor)
    return source[start:start + span]


def test_accept_and_reject_carry_their_own_outcome_tint_not_action_colour():
    """Accept carries wizard-decision-accept and Reject carries
    wizard-tag-missing - Review.dc.html:37-38's .btn-ok/.btn-no tints,
    reached here as the existing STATUS_FOUND*/STATUS_NOT_FOUND*
    tokens rather than new constants - and neither carries
    props(...color=primary...), the action-blue Specs reserves for the
    step's one primary action, which Reject is not."""
    source = _APP_PY.read_text(encoding="utf-8")
    accept_call = _call_site(source, 'ui.button("Accept"')
    reject_call = _call_site(source, 'ui.button("Reject"')
    assert "wizard-decision-accept" in accept_call
    assert "color=primary" not in accept_call
    assert "wizard-tag-missing" in reject_call
    assert "color=primary" not in reject_call


def test_a_reintroduced_action_colour_on_reject_is_caught():
    """Mutation: props("dense") is replaced with
    props("dense color=primary") on a copy of the real Reject button's
    call site, reproducing the action-blue regression this guard
    exists to catch. Observed: the same substring check
    test_accept_and_reject_carry_their_own_outcome_tint_not_action_colour
    uses finds "color=primary" present in the mutated call site, where
    it must be absent."""
    source = _APP_PY.read_text(encoding="utf-8")
    reject_call = _call_site(source, 'ui.button("Reject"')
    mutated = reject_call.replace('.props("dense")', '.props("dense color=primary")', 1)
    assert mutated != reject_call, "fixture assumption stale: props(\"dense\") not found on Reject"
    assert "color=primary" in mutated


def test_a_decided_row_renders_one_plain_undo_control():
    """app.py branches on review_model.UNDECIDED, rendering
    Review.dc.html:156's Accept/Reject pair only for an undecided row
    and Review.dc.html:148's single, untinted Undo control otherwise -
    not all three controls together the way the row used to."""
    source = _APP_PY.read_text(encoding="utf-8")
    assert "if decision == review_model.UNDECIDED:" in source
    undo_call = _call_site(source, 'ui.button("Undo"')
    assert "wizard-decision-accept" not in undo_call
    assert "wizard-tag-missing" not in undo_call
    assert "color=primary" not in undo_call


def test_a_removed_undecided_branch_is_caught():
    """Mutation: the 'if decision == review_model.UNDECIDED:' line is
    stripped from a copy of app.py's real source, standing in for the
    row losing its undecided/decided branch and going back to
    rendering all three controls unconditionally. Observed: the same
    substring check test_a_decided_row_renders_one_plain_undo_control
    uses finds it absent from the mutated copy."""
    source = _APP_PY.read_text(encoding="utf-8")
    mutated = source.replace("if decision == review_model.UNDECIDED:\n", "", 1)
    assert mutated != source, "fixture assumption stale: branch line not found"
    assert "if decision == review_model.UNDECIDED:" not in mutated
