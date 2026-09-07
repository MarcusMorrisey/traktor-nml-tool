"""Guards app._build_scan_step's run_scan against an exception escaping
scan_reconnect_candidates - M-003's own contract that every failure
reaches the operator through the assertive live region, ui.notify and
a re-enabled Start button, rather than leaving the wizard silently
dead on the Scan step.

app.py imports nicegui, which the system interpreter running this
suite does not have installed, so this file installs minimal
nicegui/webview stand-ins - the same approach
tests/test_gui_module_imports.py and tests/test_gui_accept_and_advance.py
use - before importing traktor_nml.gui.app, and tears them down
afterward. ui.button is stubbed to record the callback each on_click
call registers, keyed by the button's label, so the test can invoke
the real start_button.on_click(run_scan) callback directly instead of
driving a browser.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


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


class _FakeButton:
    """Stands in for a NiceGUI button: records the callback each
    on_click call registers so the test can invoke it directly, and
    answers every other attribute (props, classes, enable, disable, ...)
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


class _FakeUi:
    dialog = _FakeDialog

    def __init__(self) -> None:
        self.buttons_by_label: dict[str, _FakeButton] = {}
        self.notify = MagicMock()

    def button(self, label="", *args, **kwargs):
        button = _FakeButton()
        self.buttons_by_label[label] = button
        return button

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


def test_an_unexpected_scan_exception_reaches_the_operator(app_module):
    """Mutation: nicegui.run.io_bound is replaced with a coroutine that
    raises ValueError("'normal' is not a valid MatchConfidence") - the
    actual exception Defect 1 let escape scan_reconnect_candidates.
    Observed: after driving the real start_button.on_click(run_scan)
    callback to completion, state.assertive_region.set_text was called
    with a string starting with the output path (naming the file
    consequence first), ui.notify was called with the exception text,
    and start_button.enable was called - the operator is told and the
    wizard is left usable, rather than staying silently dead with the
    Start button disabled forever."""
    app_module, nicegui_module = app_module

    async def _raising_io_bound(*args, **kwargs):
        raise ValueError("'normal' is not a valid MatchConfidence")

    nicegui_module.run.io_bound = _raising_io_bound

    state = app_module._WizardPageState()
    # _page_chrome builds the footer band both routes carry, and every
    # step's advancing control is constructed in it, so a step built
    # outside a page needs the note and the action group the chrome
    # would have handed it (DL-187).
    state.footer_note = app_module.ui.label("")
    state.footer_actions = app_module.ui.row()
    state.args = __import__("argparse").Namespace(output=__import__("pathlib").Path("out.nml"))
    state.assertive_region = MagicMock()

    stepper = MagicMock()
    app_module._build_scan_step(state, stepper)

    fake_ui = nicegui_module.ui
    start_button = fake_ui.buttons_by_label["Start scan"]
    assert start_button.on_click_callback is not None, "run_scan was never registered as Start scan's on_click"

    asyncio.run(start_button.on_click_callback())

    assert start_button.enable.called, "Start button was never re-enabled after the exception"
    assert fake_ui.notify.called, "ui.notify was never called with the exception"
    assert state.assertive_region.set_text.called, "the assertive region was never told about the failure"
    announced = state.assertive_region.set_text.call_args[0][0]
    assert announced.startswith("out.nml"), announced
    assert "MatchConfidence" in announced
