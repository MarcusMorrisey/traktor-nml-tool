"""Guards app._applier_accept_and_advance's own arithmetic - accepting
a row and moving focus to the next undecided one - which
test_gui_keymap.py's applier-table guard does not reach: that guard
pins _ACTION_APPLIERS's key set against keymap.ACTION_NAMES, not what
each applier does once dispatch reaches it.

app.py imports nicegui, which the system interpreter running this
suite does not have installed, so this file installs the same minimal
nicegui/webview stand-ins tests/test_gui_module_imports.py uses before
importing traktor_nml.gui.app, and tears them down afterward.
"""

from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

from traktor_nml.gui import review_model
from traktor_nml.gui.wizard_state import WizardState
from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.review import CandidateView, RecordReview


class _FakeDialog:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        return False

    def open(self) -> None:
        """Shown and hidden by the page rather than by the framework:
        the reconstruct page's write control opens its confirmation and
        the write closes it, so the fake carries both."""

    def close(self) -> None:
        pass


class _FakeUi:
    dialog = _FakeDialog

    def __getattr__(self, name):
        return MagicMock()

    def __call__(self, *args, **kwargs):
        return MagicMock()


def _install_nicegui_stub() -> None:
    nicegui_module = types.ModuleType("nicegui")
    nicegui_module.ui = _FakeUi()
    nicegui_module.run = MagicMock()
    nicegui_module.app = MagicMock()
    nicegui_module.events = MagicMock()
    sys.modules["nicegui"] = nicegui_module
    sys.modules["webview"] = MagicMock()


def _uninstall_stub_and_app() -> None:
    for name in ("nicegui", "webview", "traktor_nml.gui.app"):
        sys.modules.pop(name, None)


@pytest.fixture
def app_module():
    _uninstall_stub_and_app()
    _install_nicegui_stub()
    try:
        yield importlib.import_module("traktor_nml.gui.app")
    finally:
        _uninstall_stub_and_app()


def _record(file_name: str) -> EntryRecord:
    return EntryRecord(
        entry=None,
        artist="A",
        title="T",
        audio_id="",
        filesize="16",
        playtime_float="1.0",
        bitrate="320",
        album="",
        file_name=file_name,
        location=LocationParts(volume="Z:", volumeid="Z:", dir_value="/:gone/:", file_name=file_name),
    )


def _matched_review(file_name: str) -> RecordReview:
    old = _record(file_name)
    winner = _record(file_name)
    return RecordReview(
        old=old,
        status="matched",
        candidates=(CandidateView(candidate=winner, key_name="filename", refuted=False),),
        chosen=winner,
        matched_by="filename",
    )


def _state_with_rows(app_module, count: int):
    """A _WizardPageState carrying `count` distinct matched reviews,
    focused on row 0, filtered on 'matched' - a filter whose predicate
    reads status alone, so accepting a row never drops it from the
    filtered rows _rows_for_filter returns."""
    state = app_module._WizardPageState()
    reviews = tuple(_matched_review(f"track{i}.mp3") for i in range(count))
    state.scan_result = app_module.ReconnectResult(
        mapping={}, stats={}, ambiguity_rows=[], old_records=[], reviews=reviews,
    )
    state.decisions = WizardState()
    state.active_filter = "matched"
    return state, reviews


def test_accept_on_a_middle_row_advances_to_the_next_undecided(app_module):
    """Mutation: none needed - this exercises the applier's own
    arithmetic directly. 4 undecided rows, focused_index=1. Observed:
    after calling the applier, row 1 is accepted and focused_index is
    2, the next row forward that is still undecided."""
    state, reviews = _state_with_rows(app_module, 4)
    state.focused_index = 1
    app_module._applier_accept_and_advance(state, {}, lambda: None)
    assert state.decisions.decision_state(reviews[1].old.primary_key) == review_model.ACCEPTED
    assert state.focused_index == 2


def test_accept_on_the_last_undecided_row_clamps(app_module):
    """Mutation: none needed. 4 rows; rows 0, 1 and 3 are already
    accepted before the call, leaving row 2 as the only undecided row,
    focused_index=2. Observed: after calling the applier, row 2 is
    accepted and focused_index stays 2 - no undecided row remains
    forward of it, so focus clamps instead of wrapping back to row 0."""
    state, reviews = _state_with_rows(app_module, 4)
    for i in (0, 1, 3):
        state.decisions.accept(reviews[i].old.primary_key)
    state.focused_index = 2
    app_module._applier_accept_and_advance(state, {}, lambda: None)
    assert state.decisions.decision_state(reviews[2].old.primary_key) == review_model.ACCEPTED
    assert state.focused_index == 2


def test_accept_skips_an_already_decided_row(app_module):
    """Mutation: none needed. 3 rows; row 1 is already accepted before
    the call, focused_index=0. Observed: after calling the applier,
    row 0 is accepted and focused_index is 2, skipping the already-
    decided row 1 rather than landing on it."""
    state, reviews = _state_with_rows(app_module, 3)
    state.decisions.accept(reviews[1].old.primary_key)
    state.focused_index = 0
    app_module._applier_accept_and_advance(state, {}, lambda: None)
    assert state.decisions.decision_state(reviews[0].old.primary_key) == review_model.ACCEPTED
    assert state.focused_index == 2
