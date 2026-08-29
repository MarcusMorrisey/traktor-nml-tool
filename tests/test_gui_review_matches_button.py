"""Guards for the Scan step's "Review matches" control
(Scanning.dc.html:166-167): disabled until a scan result exists,
enabled once one does, and - like go_to_write's own sweep - refreshes
Review through state.step_refreshers on entry rather than showing
whatever Review last rendered.

app.py imports nicegui, which the system interpreter running this
suite does not have installed, so this file installs minimal
nicegui/webview stand-ins - the same approach used by
tests/test_gui_review_step_refresh.py and
tests/test_gui_write_step_stale_count.py - before importing
traktor_nml.gui.app, and tears them down afterward.
"""

from __future__ import annotations

import argparse
import asyncio
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
    on_click call registers (constructor kwarg or .on_click(...)
    method alike), and tracks a real enabled/disabled flag rather than
    just whether enable()/disable() were ever called, so a guard can
    assert the control's *current* state."""

    def __init__(self, on_click=None) -> None:
        self.on_click_callback = on_click
        self.enabled = True

    def on_click(self, callback):
        self.on_click_callback = callback
        return self

    def enable(self):
        self.enabled = True
        return self

    def disable(self):
        self.enabled = False
        return self

    def props(self, *args, **kwargs):
        return self

    def classes(self, *args, **kwargs):
        return self


class _FakeLabel:
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
        button = _FakeButton(on_click=kwargs.get("on_click"))
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


def test_review_matches_starts_disabled_and_enables_once_a_result_exists(app_module):
    """Scanning.dc.html:167 fixes this control disabled with no result
    and enabled with one. Built with state.scan_result still None, the
    real "Review matches" button starts disabled; setting
    state.scan_result and driving the real
    start_button.on_click(run_scan) callback through a stubbed
    successful scan enables it, via run_scan's own
    _sync_review_matches_button call in its success branch."""
    app_module, nicegui_module = app_module
    fake_ui = nicegui_module.ui

    state = app_module._WizardPageState()
    state.args = argparse.Namespace(old_input=Path("stale.nml"), output=Path("out.nml"), csv=None)

    stepper = MagicMock()
    app_module._build_scan_step(state, stepper)

    review_matches_button = fake_ui.buttons_by_label["Review matches"]
    assert review_matches_button.enabled is False, "Review matches must start disabled with no scan result"

    review = _matched_review("one.mp3")
    reconnect_result = app_module.ReconnectResult(
        mapping={review.old.primary_key: review.old}, stats={}, ambiguity_rows=[], old_records=[], reviews=(review,),
    )
    scan_reconnect_result = app_module.reconnect_run.ScanReconnectResult(
        result=reconnect_result, error=None, csv_path=None,
    )

    async def _fake_io_bound(*args, **kwargs):
        return scan_reconnect_result

    nicegui_module.run.io_bound = _fake_io_bound

    start_button = fake_ui.buttons_by_label["Start scan"]
    asyncio.run(start_button.on_click_callback())

    assert review_matches_button.enabled is True, "Review matches must enable once a scan result exists"


def test_review_matches_refreshes_review_rather_than_showing_it_stale(app_module):
    """Mutation: go_to_review's own
    'for refresh_step in state.step_refreshers: refresh_step()' loop
    was manually deleted from a copy of app.py's real source and the
    test rerun against that copy - the exact regression this guard
    exists to catch, since _build_review_step still appends its own
    render_all to state.step_refreshers either way. Observed with the
    loop deleted: after state.scan_result was set directly (standing in
    for a result that landed by some path Review's own DOM has not
    seen yet) and the real "Review matches" callback driven,
    fake_ui.label_texts never gained the row-status label "matched" -
    Review's table stayed exactly as empty as it was built. Observed
    with the loop present (the code as it stands): "matched" appears in
    fake_ui.label_texts after driving the same callback."""
    app_module, nicegui_module = app_module
    fake_ui = nicegui_module.ui

    state = app_module._WizardPageState()
    state.args = argparse.Namespace(old_input=Path("stale.nml"), output=Path("out.nml"), csv=None)
    state.active_filter = "matched"

    stepper = MagicMock()
    app_module._build_scan_step(state, stepper)
    app_module._build_review_step(state, stepper)

    # Review's own build-time render_all() has already run, against
    # state.scan_result=None: no row status can exist yet.
    assert "matched" not in fake_ui.label_texts

    review = _matched_review("one.mp3")
    state.scan_result = app_module.ReconnectResult(
        mapping={review.old.primary_key: review.old}, stats={}, ambiguity_rows=[], old_records=[], reviews=(review,),
    )

    review_matches_button = fake_ui.buttons_by_label["Review matches"]
    assert review_matches_button.on_click_callback is not None, "Review matches was never registered as a button's on_click"
    review_matches_button.on_click_callback()

    assert "matched" in fake_ui.label_texts, (
        "Review matches never refreshed the review table against the current scan result"
    )