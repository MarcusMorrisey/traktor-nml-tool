"""Guards for the wizard's back navigation (Review -> Scan, Write ->
Review): the two navigation buttons themselves are cheap to pin from
source, since stepper.previous() is the only thing either does. The
guard that matters - that entering Write always recomputes its count
against current decisions - lives in
tests/test_gui_write_step_stale_count.py instead, since a
source-reading guard cannot see whether a value is stale.
"""

from __future__ import annotations

import re
from pathlib import Path

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def _call_site(source: str, anchor: str, span: int = 200) -> str:
    start = source.index(anchor)
    return source[start:start + span]


def test_review_back_button_calls_stepper_previous():
    """Review.dc.html:325's "Back" is pure navigation: on_click is
    stepper.previous directly, not a function that also touches
    state.scan_result or state.decisions."""
    source = _APP_PY.read_text(encoding="utf-8")
    call = _call_site(source, 'ui.button("Back", on_click=stepper.previous')
    assert "color=None" in call


def test_write_back_button_calls_stepper_previous():
    """Confirm.dc.html:178's "Back to review" is pure navigation:
    on_click is stepper.previous directly."""
    source = _APP_PY.read_text(encoding="utf-8")
    call = _call_site(source, 'ui.button("Back to review", on_click=stepper.previous')
    assert "color=None" in call


def test_a_removed_review_back_button_is_caught():
    """Mutation: the real "Back" button's call site on the Review step
    is stripped from a copy of app.py's real source, standing in for
    the button never having been added. Observed: the same anchor
    lookup test_review_back_button_calls_stepper_previous uses raises
    ValueError (substring not found) against the mutated copy."""
    source = _APP_PY.read_text(encoding="utf-8")
    anchor = 'ui.button("Back", on_click=stepper.previous, color=None).classes("wizard-control")'
    assert anchor in source, "fixture assumption stale: Back button call site not found"
    mutated = source.replace(anchor, "", 1)
    assert anchor not in mutated
    try:
        _call_site(mutated, 'ui.button("Back", on_click=stepper.previous')
        raised = False
    except ValueError:
        raised = True
    assert raised, "removing the Back button should make it unfindable"