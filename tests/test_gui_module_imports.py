"""Guards that every module under traktor_nml/gui/ actually imports -
not merely that its source parses as valid Python, which is all the AST
walks in tests/test_gui_view_boundary.py check. That gap is real: the
whole suite passed at 287 while traktor_nml/gui/app.py could not be
imported (`from ..rewrite import VolumeIdentityError`, when
VolumeIdentityError is defined in traktor_nml/volumes.py), because
nothing in the suite ever imported it.

The suite runs on the system interpreter, which has neither nicegui nor
pywebview installed (docs/nicegui-gui-analysis.md #5), so a plain
`import traktor_nml.gui.app` here would fail for the wrong reason - a
missing third-party package, not a real defect. This test instead
installs minimal stand-ins for `nicegui` and `webview` in sys.modules
for the duration of the test, then performs a genuine import of each
gui/ module, resolving every first-party name (traktor_nml.volumes,
traktor_nml.reconnect_run, traktor_nml.diskscan, traktor_nml.gui.*, ...)
against the real modules. Only the two third-party frameworks are
faked. sys.modules is restored in a `finally` so the fakes never leak
into another test.

The nicegui stub's `ui` object answers arbitrary attribute access with
a MagicMock (covering calls like `ui.page("/")`, `ui.column()`, ...
none of which run their decorated/nested bodies at import time - only
at request time), except `ui.dialog`, which must be a real class
because traktor_nml/gui/file_picker.py subclasses it
(`class LocalFilePicker(ui.dialog)`) - a class statement rejects a
MagicMock instance as a base.

Observed to fail against the actual bug: with `from ..rewrite import
VolumeIdentityError` reinstated in app.py (rewrite.py has no such
name), running this test raised:
    ImportError: cannot import name 'VolumeIdentityError' from
    'traktor_nml.rewrite'
confirmed by running the test with that line temporarily restored (and
the corrected `from ..volumes import VolumeIdentityError` saved aside
first, never via `git checkout`), then putting the corrected line back
and re-running to confirm it passes.
"""

from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

_GUI_MODULES = [
    "traktor_nml.gui.app",
    "traktor_nml.gui.file_picker",
    "traktor_nml.gui.__main__",
]


class _FakeDialog:
    """Stands in for nicegui's ui.dialog, which file_picker.py
    subclasses at class-definition time (import time) - a real class is
    required there since a class statement cannot use a MagicMock
    instance as a base."""

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


def _uninstall_framework_stubs_and_gui_modules() -> None:
    for name in ("nicegui", "webview", *_GUI_MODULES):
        sys.modules.pop(name, None)


def test_every_gui_module_actually_imports() -> None:
    """A real `import` of app.py, file_picker.py and __main__.py, with
    only nicegui and webview faked - every first-party name each module
    imports (traktor_nml.volumes.VolumeIdentityError,
    traktor_nml.reconnect_run.ReconnectResult, ...) is resolved against
    the genuine modules. Fails if any of the three does not import,
    which the AST-only guards in test_gui_view_boundary.py cannot
    detect since they never execute an import statement."""
    _uninstall_framework_stubs_and_gui_modules()
    _install_nicegui_stub()
    try:
        for module_name in _GUI_MODULES:
            importlib.import_module(module_name)
    finally:
        _uninstall_framework_stubs_and_gui_modules()


def _clear_app_bytecode_cache(app_path) -> None:
    """Deletes any cached .pyc for app.py and asks importlib to forget
    its cache-validity checks. Needed because this test rewrites
    app.py's source and restores it within the same wall-clock second:
    without this, Python's mtime-based pyc invalidation can treat the
    restored (correct) source as unchanged from the broken version it
    just compiled, silently keeping the broken bytecode cached on disk
    for every later test run - a real failure mode observed while
    developing this guard, not a hypothetical one."""
    pycache_dir = app_path.parent / "__pycache__"
    if pycache_dir.is_dir():
        for cached in pycache_dir.glob(f"{app_path.stem}.*.pyc"):
            cached.unlink()
    importlib.invalidate_caches()


def test_broken_reconnectresult_import_is_caught() -> None:
    """Negative control: temporarily rewrites app.py's source in place
    to the same shape of bug this guard exists to catch - importing
    ReconnectResult from ..rewrite instead of ..reconnect_run, where no
    such name exists - reads it back into the module cache the same way
    the guard above does, and records the specific ImportError observed
    before restoring the file's original text (kept in memory, never via
    `git checkout`).
    """
    app_path = (
        __import__("pathlib").Path(__file__).parent.parent
        / "traktor_nml"
        / "gui"
        / "app.py"
    )
    # newline="" on every leg of the round trip: app.py is 100% CRLF,
    # and text mode without it reads the endings away and writes back
    # os.linesep, which restores CRLF only on a host where os.linesep
    # is CRLF. Reading and writing verbatim keeps the restore correct
    # by construction rather than by host.
    original_source = app_path.read_text(encoding="utf-8", newline="")
    broken_source = original_source.replace(
        "from ..reconnect_run import ReconnectResult",
        "from ..rewrite import ReconnectResult",
        1,
    )
    assert broken_source != original_source, "expected import line not found in app.py"

    _uninstall_framework_stubs_and_gui_modules()
    _install_nicegui_stub()
    try:
        app_path.write_text(broken_source, encoding="utf-8", newline="")
        _clear_app_bytecode_cache(app_path)
        _uninstall_framework_stubs_and_gui_modules()
        _install_nicegui_stub()
        with pytest.raises(ImportError) as excinfo:
            importlib.import_module("traktor_nml.gui.app")
        assert "ReconnectResult" in str(excinfo.value)
        assert "traktor_nml.rewrite" in str(excinfo.value)
    finally:
        app_path.write_text(original_source, encoding="utf-8", newline="")
        _clear_app_bytecode_cache(app_path)
        _uninstall_framework_stubs_and_gui_modules()
