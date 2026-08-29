"""Guards that the Review step actually reflects a scan once run_scan
completes.

_build_review_step and run_scan are separate functions, and every
step is built once, up front, in index() - before any scan has run -
so _build_review_step's own render_all() call renders an empty table
against a None state.scan_result. Nothing else re-renders it:
stepper.next() only changes which step is visible. state carries the
fix - state.step_refreshers, a list _build_review_step appends its
own render_all onto, called in turn by run_scan once state.scan_result
actually holds a result - but a guard that only checks render_all was
appended to state.step_refreshers would pass even if run_scan's own
loop over it were deleted, since _build_review_step still appends it
either way. This guard instead drives the real
start_button.on_click(run_scan) callback, the production path, with
nicegui.run.io_bound stubbed to return a successful two-review scan,
and reads the table and filter chips render_table/render_filters
actually produced afterward.

app.py imports nicegui, which the system interpreter running this
suite does not have installed, so this file installs minimal
nicegui/webview stand-ins - the same approach used by
tests/test_gui_module_imports.py, tests/test_gui_accept_and_advance.py
and tests/test_gui_scan_failure.py - before importing
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
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        return False


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
    render_table row status label and every render_filters chip text
    lands there, since both call classes/set_text on whatever
    ui.label returns."""

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


def _no_match_review(file_name: str) -> RecordReview:
    old = _record(file_name)
    return RecordReview(old=old, status="unmatched", candidates=(), chosen=None, matched_by=None)


def test_review_step_reflects_the_scan_once_run_scan_completes(app_module):
    """Mutation: deleting run_scan's loop over state.step_refreshers
    in the success branch - the exact regression this guard exists to
    catch, since _build_review_step still appends render_all to that
    list either way - was manually verified to make this test fail
    with an AssertionError on the missing matched row-status label.
    Observed with the loop present: driving the real
    start_button.on_click(run_scan) callback through a stubbed
    successful two-review scan (one matched, one unmatched) produces
    the row-status label matched in fake_ui.label_texts and the
    filter chip button Not found (1) in fake_ui.buttons_by_label,
    neither of which was there after
    _build_review_step's own build-time render_all(), which ran
    against state.scan_result=None and produced no row-status label at
    all."""
    app_module, nicegui_module = app_module
    fake_ui = nicegui_module.ui

    state = app_module._WizardPageState()
    state.args = argparse.Namespace(output=Path("out.nml"), csv=None)
    # QUEUE_FILTER_KEYS[0] ("ambiguous") is the default active_filter,
    # which would exclude both fixture rows below (matched, no_match)
    # from the table regardless of whether the refresh ran - "matched"
    # is one of the seven FILTERS keys, so this keeps the assertion
    # about the refresh honest rather than about the filter choice.
    state.active_filter = "matched"

    stepper = MagicMock()
    app_module._build_scan_step(state, stepper)
    app_module._build_review_step(state, stepper)

    # _build_review_step's own build-time render() has already run,
    # against state.scan_result=None: no row status can exist yet.
    assert "matched" not in fake_ui.label_texts

    reviews = (_matched_review("one.mp3"), _no_match_review("two.mp3"))
    reconnect_result = app_module.ReconnectResult(
        mapping={}, stats={}, ambiguity_rows=[], old_records=[], reviews=reviews,
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
    assert "matched" in fake_ui.label_texts, (
        "the review table never rendered a matched row after the scan completed"
    )
    # render_filters creates the seven filter chips as ui.button(text, ...),
    # not ui.label - text is "{label} ({count})", so this is the "Not
    # found" chip's count picking up the one no_match review.
    assert "Not found (1)" in fake_ui.buttons_by_label, (
        "the filter chips never picked up the scan counts"
    )
