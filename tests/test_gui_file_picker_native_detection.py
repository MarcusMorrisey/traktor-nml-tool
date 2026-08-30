"""Guard for traktor_nml/gui/file_picker.py's native-mode detection.

The bug this exists to catch: app.py hardcoded `native=True` at both of
its pick_file_or_folder call sites, so pick_file()/pick_folder() always
ran their `if not webview.windows: return None` guard and returned None
the moment the wizard was served over HTTP instead of a pywebview
window - the LocalFilePicker fallback class existed but was never
reachable in that configuration. Fails silently: no dialog, no
exception, no notification.

pick_file_or_folder defaults `native=None` ("detect") and decides
through native_window(), so there is exactly one place in the codebase
that decides what "native" means. That helper reads
app.native.main_window: NiceGUI builds its pywebview window in a
separate spawned process, so webview.windows is empty in the server
process under ui.run(native=True) as well as under an HTTP serve, and
cannot distinguish them.

This suite runs on an interpreter with no nicegui/pywebview installed
(docs/nicegui-gui-analysis.md #5), so it follows
tests/test_gui_module_imports.py's pattern: install minimal stand-ins
for `nicegui` and `webview` in sys.modules for the duration of the
test, import traktor_nml.gui.file_picker for real against them, and
restore sys.modules in a `finally` so the fakes never leak into
another test.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_MODULE_NAME = "traktor_nml.gui.file_picker"


class _FakeDialog:
    """Stands in for nicegui's ui.dialog, which LocalFilePicker
    subclasses at class-definition time (import time) - a real class is
    required there since a class statement cannot use a MagicMock
    instance as a base."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        return False


class _FakeUi:
    dialog = _FakeDialog

    def __getattr__(self, name):
        return MagicMock()

    def __call__(self, *args, **kwargs):
        return MagicMock()


def _install_stubs(windows: list, main_window=None) -> None:
    nicegui_module = types.ModuleType("nicegui")
    nicegui_module.ui = _FakeUi()
    nicegui_module.run = MagicMock()
    # app.native.main_window is the detection signal, so it is a real
    # object with a real attribute rather than a MagicMock: every
    # attribute of a MagicMock is itself a truthy MagicMock, which would
    # make "no native window" indistinguishable from "native window" and
    # so make this suite unable to fail.
    app_module = types.SimpleNamespace(native=types.SimpleNamespace(main_window=main_window))
    nicegui_module.app = app_module
    nicegui_module.events = MagicMock()
    sys.modules["nicegui"] = nicegui_module

    webview_module = types.ModuleType("webview")
    webview_module.windows = windows
    webview_module.FileDialog = MagicMock()
    sys.modules["webview"] = webview_module


def _uninstall_stubs_and_module() -> None:
    for name in ("nicegui", "webview", _MODULE_NAME):
        sys.modules.pop(name, None)


class _FakeWindowProxy:
    """Stands in for nicegui.native.native.WindowProxy: create_file_dialog
    is a coroutine there, because the real one marshals the call to the
    process that owns the window."""

    def __init__(self, result) -> None:
        self._result = result
        self.calls: list = []

    async def create_file_dialog(self, dialog_type=None, **kwargs):
        self.calls.append((dialog_type, kwargs))
        return self._result


def test_window_in_another_process_still_routes_to_the_native_dialog() -> None:
    """NiceGUI builds its pywebview window in a separate spawned process
    (nicegui/native/native_mode.py: SPAWN_CONTEXT.Process), so
    webview.windows is empty in the server process even under
    ui.run(native=True). Detection must therefore read
    app.native.main_window, which that process does hold.

    Observed to fail against the actual bug: with `bool(webview.windows)`
    as the detection expression and the stubs below - windows=[] and a
    WindowProxy present, which is exactly the running native app - the
    call routed to LocalFilePicker and returned
    Path('/fallback/chosen'), so a native run got the in-page filesystem
    browser and pywebview's own dialog was unreachable in every
    configuration. With the fixed expression the same stubs reach the
    proxy and return Path('/native/chosen').
    """
    _uninstall_stubs_and_module()
    window = _FakeWindowProxy(result=("/native/chosen",))
    _install_stubs(windows=[], main_window=window)
    try:
        file_picker_module = importlib.import_module(_MODULE_NAME)

        constructed: list = []

        class _FakeLocalFilePicker:
            def __init__(self, *args, **kwargs) -> None:
                constructed.append((args, kwargs))

            def __await__(self):
                async def _resolve():
                    return ["/fallback/chosen"]

                return _resolve().__await__()

        file_picker_module.LocalFilePicker = _FakeLocalFilePicker

        result = asyncio.run(
            file_picker_module.pick_file_or_folder(directories_only=True)
        )
        assert result == Path("/native/chosen")
        assert window.calls, "the window proxy's create_file_dialog was never awaited"
        assert not constructed, "a native window must not reach the LocalFilePicker fallback"
    finally:
        _uninstall_stubs_and_module()


def test_no_native_window_routes_to_local_file_picker_fallback() -> None:
    """With webview.windows empty (the HTTP-served, non-native case) and
    native left at its default (None, "detect"), pick_file_or_folder must
    reach LocalFilePicker rather than returning None outright - that is
    the property whose absence made the original bug invisible.

    Observed to fail against the actual bug: reproduced below by calling
    pick_file_or_folder(native=True) - the value app.py used to hardcode
    at both call sites - with the same empty webview.windows. That call
    returns None without ever touching file_picker_module.LocalFilePicker,
    reproducing the silent no-dialog failure exactly.
    """
    _uninstall_stubs_and_module()
    _install_stubs(windows=[])
    try:
        file_picker_module = importlib.import_module(_MODULE_NAME)

        constructed: list = []

        class _FakeLocalFilePicker:
            def __init__(self, *args, **kwargs) -> None:
                constructed.append((args, kwargs))

            def __await__(self):
                async def _resolve():
                    return ["/fallback/chosen"]

                return _resolve().__await__()

        file_picker_module.LocalFilePicker = _FakeLocalFilePicker

        # Fixed behavior: native defaults to "detect", which finds no
        # window and routes to the fallback.
        result = asyncio.run(
            file_picker_module.pick_file_or_folder(directories_only=True)
        )
        assert constructed, "LocalFilePicker was never constructed - fallback not reached"
        assert result == Path("/fallback/chosen")

        # Reproduction of the actual bug: forcing native=True (what
        # app.py used to hardcode) skips the fallback entirely and
        # returns None, with LocalFilePicker never constructed again.
        constructed.clear()
        broken_result = asyncio.run(
            file_picker_module.pick_file_or_folder(native=True, directories_only=True)
        )
        assert broken_result is None
        assert not constructed, "hardcoded native=True must not reach the fallback"
    finally:
        _uninstall_stubs_and_module()
