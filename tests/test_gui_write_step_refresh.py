"""Guards that the Write step actually reflects a scan once run_scan
completes.

_build_write_step and run_scan are separate functions, and every step
is built once, up front, in index() - before any scan has run - so
_build_write_step's own render() call, at build time, finds
state.scan_result is still None and renders only "Nothing to write.".
Nothing else re-renders it: stepper.next() only changes which step is
visible. state carries the fix - state.step_refreshers, the same list
tests/test_gui_review_step_refresh.py's guard exercises for the
Review step, onto which _build_write_step appends its own render -
but a guard that only checks render was appended to
state.step_refreshers would pass even if run_scan's own loop over it
were deleted, since _build_write_step still appends it either way.
This guard instead drives the real start_button.on_click(run_scan)
callback, the production path, with nicegui.run.io_bound stubbed to
return a successful one-match scan, and reads what the Write step
actually rendered afterward - and separately confirms a cancelled
scan still lands on "Nothing to write." on refresh, not only on the
step's first, build-time render.

app.py imports nicegui, which the system interpreter running this
suite does not have installed, so this file installs minimal
nicegui/webview stand-ins - the same approach used by
tests/test_gui_module_imports.py, tests/test_gui_accept_and_advance.py,
tests/test_gui_scan_failure.py and
tests/test_gui_review_step_refresh.py - before importing
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


class _FakeDialog:
    """Stands in for nicegui's ui.dialog: open/close are targets
    _build_write_step's confirm dialog wires up as callbacks
    (write_button.on_click(dialog.open), the Cancel button's
    on_click=dialog.close), so both need to be callable, not merely
    absent attributes. on(...) stands in for the Quasar 'hide' event
    subscription the focus-return fix registers."""

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
    set_text call sets, in order, in the shared sink list. Every
    render() text, including "Nothing to write." and the reconnect-
    count label, lands there, since both call classes/set_text on
    whatever ui.label returns."""

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


def test_write_step_reflects_the_scan_once_run_scan_completes(app_module):
    """Mutation: deleting run_scan's loop over state.step_refreshers -
    the exact regression this guard exists to catch, since
    _build_write_step still appends render to that list either way -
    was manually verified to make this test fail with an
    AssertionError on the missing "1 tracks to reconnect" label.
    Observed with the loop present: driving the real
    start_button.on_click(run_scan) callback through a stubbed
    successful one-match scan produces the label "1 tracks to
    reconnect" and the "Write output" button in
    fake_ui.buttons_by_label, neither of which was there after
    _build_write_step's own build-time render(), which ran against
    state.scan_result=None and produced only "Nothing to write."."""
    app_module, nicegui_module = app_module
    fake_ui = nicegui_module.ui

    state = app_module._WizardPageState()
    state.args = argparse.Namespace(
        old_input=Path("stale.nml"), output=Path("out.nml"), csv=None,
    )

    stepper = MagicMock()
    app_module._build_scan_step(state, stepper)
    app_module._build_write_step(state, stepper)

    # _build_write_step's own build-time render() has already run,
    # against state.scan_result=None: only the placeholder can exist.
    assert "Nothing to write." in fake_ui.label_texts
    assert "Write output" not in fake_ui.buttons_by_label

    reconnect_result = app_module.ReconnectResult(
        mapping={"one": _record("one.mp3")}, stats={}, ambiguity_rows=[], old_records=[], reviews=(),
    )
    scan_reconnect_result = app_module.reconnect_run.ScanReconnectResult(
        result=reconnect_result, error=None, csv_path=None,
    )

    async def _fake_io_bound(*args, **kwargs):
        return scan_reconnect_result

    nicegui_module.run.io_bound = _fake_io_bound

    start_button = fake_ui.buttons_by_label["Start scan"]
    assert start_button.on_click_callback is not None, "run_scan was never registered as Start scan on_click"

    asyncio.run(start_button.on_click_callback())

    assert state.scan_result is reconnect_result
    assert "1 tracks to reconnect" in fake_ui.label_texts, (
        "the Write step never rendered the reconnect count after the scan completed"
    )
    assert "Write output" in fake_ui.buttons_by_label, (
        "the Write step never rendered its write button after the scan completed"
    )


def test_a_cancelled_scan_still_refreshes_to_nothing_to_write(app_module):
    """Mutation: none needed - this exercises state.cancelled being
    re-checked on every refresh, not assumed false once a scan result
    exists, per the coordinator's explicit requirement. Observed:
    after driving run_scan through a cancelled scan (nicegui.run.io_bound
    raises the real ScanCancelled reconnect_run.scan_reconnect_candidates
    raises), fake_ui.label_texts gains a second "Nothing to write."
    entry from the refresh, appended after the one from the step's own
    build-time render, and no reconnect-count label or write button is
    ever added."""
    app_module, nicegui_module = app_module
    fake_ui = nicegui_module.ui

    state = app_module._WizardPageState()
    state.args = argparse.Namespace(
        old_input=Path("stale.nml"), output=Path("out.nml"), csv=None,
    )

    stepper = MagicMock()
    app_module._build_scan_step(state, stepper)
    app_module._build_write_step(state, stepper)

    assert fake_ui.label_texts.count("Nothing to write.") == 1

    async def _cancelling_io_bound(*args, **kwargs):
        raise app_module.ScanCancelled()

    nicegui_module.run.io_bound = _cancelling_io_bound

    start_button = fake_ui.buttons_by_label["Start scan"]
    asyncio.run(start_button.on_click_callback())

    assert state.cancelled is True
    assert fake_ui.label_texts.count("Nothing to write.") == 2
    assert "Write output" not in fake_ui.buttons_by_label
