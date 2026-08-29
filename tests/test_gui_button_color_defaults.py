"""Guards that every ui.button(...) call in app.py states its colour
intent at the constructor - the only place that decides it.

ui.button's own color parameter defaults to "primary" (NiceGUI's
button.py) regardless of what .props() carries. Quasar renders that
default as its own bg-primary/text-white (or, combined with an
outline prop, text-primary) utility classes, and every one of those
utilities carries !important in the bundled quasar.important.css - so
no class this module attaches, however specific its selector, could
ever have outranked them. A source-reading guard that only checks a
tint class is attached (tests/test_gui_review_row_controls.py's own
tint guard) cannot see this: the class was there, attached, correct,
and still lost. The only fix is at the constructor, so this is the
only place a guard can usefully look.

Each ui.button(...) call below is checked for an explicit color=
argument - never left to the default - naming it either color=None
(a plain or token-tinted control, so Quasar's own utilities never
apply) or color="primary" (a deliberate primary action). Which is
which, and why, is recorded per call.
"""

from __future__ import annotations

import re
from pathlib import Path

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"

# One entry per ui.button(...) call in app.py, keyed by a literal
# substring unique to that call, naming the color= argument it must
# carry and why:
#
# color=None - plain or already-token-tinted controls, where Quasar's
# own primary utilities would either paint over an intentionally
# neutral control or fight a status token this module already applies:
#   "Choose collection file..." (Main.dc.html:97 plain .btn)
#   "Add scan root..." (no artboard; a second primary competing with
#     Set up's own "Continue" would violate Specs' single-primary-
#     action principle - a judgement call, not a citation)
#   the Scan step's "Cancel" (Scanning.dc.html:166 fixes this as
#     .btn-dgr, not .btn-pri or plain .btn; color=None only removes
#     the definitely-wrong primary blue - the danger tint itself is a
#     separate, unimplemented finding)
#   "Accept" (wizard-decision-accept), "Reject" (wizard-tag-missing),
#     "Undo" (Review.dc.html:37-38/:148)
#   the filter chips (wizard-tag-action / wizard-tag-action-outline)
#   the confirm dialog's "Cancel" / safe_button (Confirm.dc.html:159
#     plain .btn)
#
#   the five .btn-pri controls - Set up's "Continue", the Scan step's
#     "Start scan", the Review step's "Continue to write", the Write
#     step's "Write output" (Results.dc.html's .btn-pri) and the confirm
#     dialog's "Write" (Confirm.dc.html:160's .btn-pri). Each is the one
#     primary action on its step or dialog and each renders the action
#     blue, but through wizard-control-primary rather than through
#     Quasar's color="primary": that utility pairs bg-primary with
#     text-white, and text-white holds the label at 2.31:1 against the
#     blue where the artboard's own ink measures 8.2:1. Both utilities
#     are !important in the layer Quasar orders last, so the ink arrives
#     only when the constructor withholds the colour and the token class
#     carries the background with it - DL-086's rung one, every rung
#     measured in docs/2026-08-29-w004-focus-ring-record.md.
#
# color="primary" - no call carries it. A call that does has left its
# label to Quasar's text-white, which is the defect above.
_EXPECTED_COLOR_BY_CALL = {
    '"Choose collection file..."': "None",
    '"Add scan root..."': "None",
    '"Continue", on_click=go_to_scan': "None",
    'cancel_button = ui.button("Cancel"': "None",
    'start_button = ui.button("Start scan"': "None",
    '"Accept", on_click=lambda k=key: (state.decisions.accept(k)': "None",
    '"Reject", on_click=lambda k=key: (state.decisions.reject(k)': "None",
    '"Undo", on_click=lambda k=key: (state.decisions.undo(k)': "None",
    'ui.button(filter_text,': "None",
    '"Continue to write", on_click=go_to_write': "None",
    'write_button = ui.button("Write output"': "None",
    'safe_button = ui.button("Cancel", on_click=dialog.close': "None",
    '"Write", on_click=lambda: (dialog.close(), _do_write())': "None",
}

_CALL_SPAN = 200


def _actual_colors(source: str) -> dict:
    """For each named call, the literal color=... argument its own
    ui.button(...) call carries in the real source, read within
    _CALL_SPAN characters after the anchor - None if no color=
    argument is found at all (the accidental-default shape every one
    of these calls used to have)."""
    found = {}
    for anchor in _EXPECTED_COLOR_BY_CALL:
        start = source.index(anchor)
        window = source[start:start + _CALL_SPAN]
        match = re.search(r"color=(None|\"primary\")", window)
        found[anchor] = match.group(1) if match else None
    return found


def test_every_button_states_its_colour_at_the_constructor():
    """Every ui.button(...) call this module cares about carries an
    explicit color= argument matching _EXPECTED_COLOR_BY_CALL - never
    left unstated, which is the shape of the accidental-primary defect
    this guard exists to catch."""
    source = _APP_PY.read_text(encoding="utf-8")
    actual = _actual_colors(source)
    assert actual == _EXPECTED_COLOR_BY_CALL, (
        f"button colour mismatch: {[(k, v) for k, v in actual.items() if v != _EXPECTED_COLOR_BY_CALL[k]]}"
    )


def test_a_dropped_colour_argument_is_caught():
    """Mutation: the real "Accept" button's call site has its
    ", color=None" argument stripped from a copy of app.py's real
    source, reproducing the exact defect this guard exists to catch -
    a control meant to carry wizard-decision-accept silently falling
    back to ui.button's own "primary" default. Observed: the same
    extraction test_every_button_states_its_colour_at_the_constructor
    uses reports None (no color= argument found at all) for that call
    site, against the expected "None" (an explicit color=None
    argument) - two different things equality catches."""
    source = _APP_PY.read_text(encoding="utf-8")
    anchor = '"Accept", on_click=lambda k=key: (state.decisions.accept(k)'
    start = source.index(anchor)
    end = start + _CALL_SPAN
    mutated_window = source[start:end].replace(", color=None", "", 1)
    assert mutated_window != source[start:end], "fixture assumption stale: ', color=None' not found"
    match = re.search(r"color=(None|\"primary\")", mutated_window)
    assert match is None
