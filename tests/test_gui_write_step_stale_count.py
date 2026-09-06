"""Guards that entering the Write step always recomputes its reconnect
count and refusal against the operator's current decisions, not
whatever they were the first time Write rendered.

_build_review_step and _build_write_step are separate functions, both
built once, up front, in index(), against whatever state.scan_result
already holds. Once the operator has visited Write once, a
Write -> Back to review -> revise a decision -> Continue to write
round trip changes state.decisions without ever touching
state.scan_result - nothing about a fresh scan happens - so the only
thing that can catch Write's own rendered count up to the revised
decision is go_to_write itself calling back into state.step_refreshers
before stepper.next(). A guard that only checks state.step_refreshers
contains Write's render (the way _build_write_step always appends it)
would pass even if go_to_write's own sweep were deleted, since nothing
else would call it. This guard instead drives the real
"Reject" and "Continue to write" button callbacks, the production
path, and reads what the Write step actually rendered afterward.

app.py imports nicegui, which the system interpreter running this
suite does not have installed, so this file installs minimal
nicegui/webview stand-ins - the same approach used by
tests/test_gui_review_step_refresh.py and
tests/test_gui_write_step_refresh.py - before importing
traktor_nml.gui.app, and tears them down afterward.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.review import CandidateView, RecordReview


class _FakeDialog:
    def __init__(self, *args, **kwargs) -> None:
        self.open = MagicMock()
        self.close = MagicMock()
        self.on = MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        return False

    def props(self, *args, **kwargs):
        return self


class _FakeButton:
    """Stands in for a NiceGUI button: records the callback each
    on_click call registers so the test can invoke it directly, and
    answers every other attribute (props, classes, enable, disable)
    with a MagicMock."""

    def __init__(self) -> None:
        self.on_click_callback = None
        self.enable = MagicMock()
        self.disable = MagicMock()

    def on_click(self, callback):
        self.on_click_callback = callback
        return self

    def props(self, *args, **kwargs):
        return self

    def classes(self, *args, **kwargs):
        return self


class _FakeLabel:
    """Stands in for a NiceGUI label: records the text every
    set_text call sets, in order, in the shared sink list."""

    def __init__(self, initial_text: str, sink: list) -> None:
        self._sink = sink
        if initial_text:
            sink.append(initial_text)

    def set_text(self, text):
        self._sink.append(text)

    def classes(self, *args, **kwargs):
        return self

    def props(self, *args, **kwargs):
        return self

    def set_visibility(self, visible):
        return self


class _FakeUi:
    dialog = _FakeDialog

    def __init__(self) -> None:
        self.buttons_by_label: dict[str, _FakeButton] = {}
        self.label_texts: list[str] = []
        self.notify = MagicMock()

    def button(self, label="", *args, **kwargs):
        button = _FakeButton()
        if kwargs.get("on_click") is not None:
            button.on_click_callback = kwargs["on_click"]
        self.buttons_by_label[label] = button
        return button

    def label(self, text="", *args, **kwargs):
        return _FakeLabel(text, self.label_texts)

    def __getattr__(self, name):
        return MagicMock()

    def __call__(self, *args, **kwargs):
        return MagicMock()


def _install_nicegui_stub() -> types.ModuleType:
    nicegui_module = types.ModuleType("nicegui")
    nicegui_module.ui = _FakeUi()
    nicegui_module.run = MagicMock()
    nicegui_module.app = MagicMock()
    nicegui_module.events = MagicMock()
    sys.modules["nicegui"] = nicegui_module
    sys.modules["webview"] = MagicMock()
    return nicegui_module


def _uninstall_stub_and_app() -> None:
    for name in ("nicegui", "webview", "traktor_nml.gui.app"):
        sys.modules.pop(name, None)


@pytest.fixture
def app_module():
    _uninstall_stub_and_app()
    nicegui_module = _install_nicegui_stub()
    try:
        module = importlib.import_module("traktor_nml.gui.app")
        yield module, nicegui_module
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


def _ambiguous_review(file_name: str) -> RecordReview:
    old = _record(file_name)
    a = _record(file_name)
    return RecordReview(
        old=old,
        status="ambiguous",
        candidates=(CandidateView(candidate=a, key_name="filename", refuted=False),),
        chosen=None,
        matched_by=None,
    )


def _build_state_with_one_ambiguous_review(app_module):
    """A state whose scan already completed with one ambiguous review,
    already in result.mapping under its own key (as a matched-but-
    ambiguous cascade winner would be) - review_model.QUEUE_FILTER_KEYS[0]
    ("ambiguous") is the default active_filter, so the row renders
    without needing to switch filters first."""
    state = app_module._WizardPageState()
    # _page_chrome builds the footer band both routes carry, and every
    # step's advancing control is constructed in it, so a step built
    # outside a page needs the note and the action group the chrome
    # would have handed it (DL-187).
    state.footer_note = app_module.ui.label("")
    state.footer_actions = app_module.ui.row()
    state.args = argparse.Namespace(old_input=Path("stale.nml"), output=Path("out.nml"), csv=None)
    review = _ambiguous_review("track.mp3")
    key = review.old.primary_key
    state.scan_result = app_module.ReconnectResult(
        mapping={key: review.old}, stats={}, ambiguity_rows=[], old_records=[], reviews=(review,),
    )
    return state, review


def test_write_step_recomputes_the_count_on_every_entry(app_module):
    """Mutation: go_to_write's own
    'for refresh_step in state.step_refreshers: refresh_step()' loop
    was manually deleted from a copy of app.py's real source and the
    test rerun against that copy - the exact regression this guard
    exists to catch, since _build_write_step still appends its own
    render to state.step_refreshers either way, so a guard checking
    only that the append happened would still pass. Observed with the
    loop deleted: after driving the real "Reject" then "Continue to
    write" button callbacks, fake_ui.label_texts contained only the
    stale "1 tracks to reconnect" from Write's initial build-time
    render, and never "0 tracks to reconnect" - Write's own render()
    never ran again despite Continue to write being clicked. Observed
    with the loop present (the code as it stands): "0 tracks to
    reconnect" appears in fake_ui.label_texts, computed from
    wizard_state.apply(state.scan_result, state.decisions) against the
    revised (rejected) decision, not the undecided one Write first
    rendered against."""
    app_module, nicegui_module = app_module
    fake_ui = nicegui_module.ui

    state, review = _build_state_with_one_ambiguous_review(app_module)
    key = review.old.primary_key

    stepper = MagicMock()
    app_module._build_review_step(state, stepper)
    app_module._build_write_step(state, stepper)

    # Write's own build-time render() already ran against the
    # undecided review: the ambiguous entry is still in result.mapping
    # (an ambiguous status carries no decision yet), so
    # wizard_state.apply reports it as one track to reconnect.
    assert "1 tracks to reconnect" in fake_ui.label_texts
    expected_before = len(app_module.wizard_state.apply(state.scan_result, state.decisions))
    assert expected_before == 1

    reject_button = fake_ui.buttons_by_label["Reject"]
    assert reject_button.on_click_callback is not None, "Reject was never registered as a button's on_click"
    reject_button.on_click_callback()

    assert state.decisions.decision_state(key) == "left_missing"
    expected_after = len(app_module.wizard_state.apply(state.scan_result, state.decisions))
    assert expected_after == 0

    continue_button = fake_ui.buttons_by_label["Continue to write"]
    assert continue_button.on_click_callback is not None, "Continue to write was never registered as a button's on_click"
    continue_button.on_click_callback()

    assert "0 tracks to reconnect" in fake_ui.label_texts, (
        "Write step never recomputed its reconnect count against the revised decision"
    )