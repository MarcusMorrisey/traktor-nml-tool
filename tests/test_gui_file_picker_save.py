"""pick_save_path's normalisation of pywebview's SAVE dialog result.

file_picker.py imports nicegui and webview, which the system interpreter
lacks; this module installs the stand-ins
tests/test_build_playlist_byte_identity.py uses and removes them in a
finally so they never leak into another test.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

from tests.test_build_playlist_byte_identity import _install_nicegui_stub, _uninstall


class _StubWindow:
    def __init__(self, result) -> None:
        self.result = result
        self.calls: list[tuple] = []

    async def create_file_dialog(self, dialog_type, **kwargs):
        self.calls.append((dialog_type, kwargs))
        return self.result


def _pick(result):
    _uninstall()
    _install_nicegui_stub()
    try:
        file_picker = importlib.import_module("traktor_nml.gui.file_picker")
        window = _StubWindow(result)
        path = asyncio.run(file_picker.pick_save_path(window, save_filename="playlist-template.csv"))
        dialog_type = window.calls[0][0]
        expected_type = sys.modules["webview"].FileDialog.SAVE
        return path, window.calls[0][1], dialog_type is expected_type
    finally:
        _uninstall()


def test_pick_save_path_accepts_a_string() -> None:
    """A str result is the chosen path, asked for through the SAVE
    dialog with the template's file name.

    Mutation: pick_save_path returns Path(result[0]) for every non-empty
        result, so the str result 'C:/out/t.csv' becomes Path('C').
    Observed:
        E       AssertionError: assert WindowsPath('C') == WindowsPath('C:/out/t.csv')
        E        +  where WindowsPath('C:/out/t.csv') = Path('C:/out/t.csv')
    """
    path, kwargs, is_save = _pick("C:/out/t.csv")
    assert path == Path("C:/out/t.csv")
    assert kwargs["save_filename"] == "playlist-template.csv"
    assert is_save


def test_pick_save_path_accepts_a_sequence() -> None:
    """A one-element sequence result is the chosen path: the other shape
    pywebview returns from a SAVE dialog.

    Mutation: pick_save_path returns Path(result) when result is a str
        and None for any other shape, so the one-element tuple reads as
        cancel.
    Observed:
        E       AssertionError: assert None == WindowsPath('C:/out/t.csv')
        E        +  where WindowsPath('C:/out/t.csv') = Path('C:/out/t.csv')
    """
    path, _kwargs, _is_save = _pick(("C:/out/t.csv",))
    assert path == Path("C:/out/t.csv")


def test_pick_save_path_cancel_is_none() -> None:
    """None, an empty string and an empty sequence all mean cancel.

    Mutation: pick_save_path treats only None as cancel, so the empty
        string returns Path('') in place of None.
    Observed:
        E           AssertionError: assert WindowsPath('.') is None
    """
    for cancelled in (None, "", (), [""]):
        path, _kwargs, _is_save = _pick(cancelled)
        assert path is None
