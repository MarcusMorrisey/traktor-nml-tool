"""Guard for traktor_nml/gui/file_picker.py's native-mode detection.

The bug this exists to catch: app.py hardcoded `native=True` at both of
its pick_file_or_folder call sites, so pick_file()/pick_folder() always
ran their `if not webview.windows: return None` guard and returned None
the moment the wizard was served over HTTP instead of a pywebview
window - the LocalFilePicker fallback class existed but was never
reachable in that configuration. Fails silently: no dialog, no
exception, no notification.

pick_file_or_folder now defaults `native=None` ("detect") and decides
by reading webview.windows itself - the same attribute pick_file/
pick_folder already consult - so there is exactly one place in the
codebase that decides what "native" means.

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


def _install_stubs(windows: list) -> None:
    nicegui_module = types.ModuleType("nicegui")
    nicegui_module.ui = _FakeUi()
    nicegui_module.run = MagicMock()
    nicegui_module.app = MagicMock()
    nicegui_module.events = MagicMock()
    sys.modules["nicegui"] = nicegui_module

    webview_module = types.ModuleType("webview")
    webview_module.windows = windows
    webview_module.FileDialog = MagicMock()
    sys.modules["webview"] = webview_module


def _uninstall_stubs_and_module() -> None:
    for name in ("nicegui", "webview", _MODULE_NAME):
        sys.modules.pop(name, None)


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
