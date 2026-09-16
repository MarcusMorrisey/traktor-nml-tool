"""Guards that the build-playlist GUI's write path
(traktor_nml/gui/app.py::_run_build_playlist) produces output bytes
byte-for-byte identical to build_playlist_cmd.py's own CLI handler for
the same inputs - the MUST NOT constraint that the GUI never diverges
from the CLI's own behaviour or output bytes (DL-262), which M-003's
requirements state but which no source-reading AST guard can check on
its own: two functions can each call buildplaylist.assemble_output
correctly and still disagree on the isolation pass or the atomic write
around it.

Importing traktor_nml.gui.app needs nicegui installed, which the
system interpreter lacks; this test installs the same minimal stand-in
tests/test_gui_module_imports.py uses so a genuine import resolves
every first-party name, and restores sys.modules in a finally so the
stand-ins never leak into another test.
"""

from __future__ import annotations

import importlib
import sys
import types
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.conftest import run_tool

# playlists.py stamps a fresh uuid.uuid4().hex onto every synthesized
# PLAYLIST node (DL-008), so two independent runs over identical inputs
# never agree byte-for-byte on their own - the divergence this test
# exists to catch is everywhere else in the output. Both the CLI call
# and the GUI call below are patched to this same fixed value so a
# genuine behavioural difference is what the comparison is left to
# catch, not this expected, unrelated source of randomness.
_FIXED_UUID = uuid.UUID("00000000-0000-4000-8000-000000000000")

_GUI_MODULES = ["traktor_nml.gui.app", "traktor_nml.gui.file_picker", "traktor_nml.gui.__main__"]


class _FakeDialog:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        return False

    def open(self) -> None:
        pass

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


def _uninstall() -> None:
    for name in ("nicegui", "webview", *_GUI_MODULES):
        sys.modules.pop(name, None)


def _nml(entries_xml: str, entries_count: int) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0">'
        "</SUBNODES></NODE></PLAYLISTS>"
        "<SETS></SETS><INDEXING></INDEXING></NML>"
    )


def _entry(artist: str, title: str, filename: str) -> str:
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="/:Music/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
        '<INFO BITRATE="320" PLAYTIME_FLOAT="1.0" FILESIZE="16"></INFO>'
        "</ENTRY>"
    )


def test_gui_write_path_matches_cli_output_bytes(tmp_path: Path) -> None:
    """The GUI's _run_build_playlist and the CLI's build-playlist
    handler, run against the same fixture base collection and track
    list, write byte-identical files. The base collection carries a
    third entry the track list never names, so a full-collection
    output and an isolated one actually differ on this fixture rather
    than coinciding by accident.

    Made to fail by inverting _run_build_playlist's `if not
    inputs.full_collection:` to `if inputs.full_collection:` - with
    full_collection False (this test's own input), that skips the
    isolation pass build_playlist_cmd.py's handler always takes by
    default, so the GUI's file keeps the third, unreferenced entry
    while the CLI's does not. Observed:
        AssertionError: assert b'<?xml versi...DEXING></NML>' ==
        b'<?xml versi...DEXING></NML>'
        At index 138 diff: b'3' != b'2'
    """
    # A third entry the track list never names: irrelevant to a full-
    # collection output, which keeps it, but dropped by the isolation
    # pass every default (non --full-collection) run takes - the one
    # difference this fixture needs to actually exercise the isolation
    # branch rather than coincide with its own absence.
    base = tmp_path / "base.nml"
    base.write_text(
        _nml(
            _entry("A", "One", "one.mp3")
            + _entry("B", "Two", "two.mp3")
            + _entry("C", "Three", "three.mp3"),
            3,
        ),
        encoding="utf-8",
        newline="",
    )
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\nB - Two\n", encoding="utf-8")

    cli_out = tmp_path / "cli.nml"
    with patch("uuid.uuid4", return_value=_FIXED_UUID):
        result = run_tool(
            ["build-playlist", str(base), str(tracklist), str(cli_out), "--name", "MyList"],
            cwd=tmp_path,
        )
    assert result.exit_code == 0
    cli_bytes = cli_out.read_bytes()

    _uninstall()
    _install_nicegui_stub()
    try:
        app = importlib.import_module("traktor_nml.gui.app")
        inputs = app.FormInputs(
            base_path=str(base),
            tracklist_path=str(tracklist),
            name="MyList",
            target_folder="",
            allow_unmatched=False,
            full_collection=False,
        )
        with patch("uuid.uuid4", return_value=_FIXED_UUID):
            gui_result = app._run_build_playlist(inputs)
        assert gui_result.output is not None, gui_result.errors
        # _run_build_playlist writes the file itself, at the path
        # _derive_build_playlist_output_path derives from name and
        # target_folder (DL-272) - the same path this fixture's empty
        # target_folder derives, base's own directory.
        gui_output_path = app._derive_build_playlist_output_path(base, "MyList", "")
        gui_bytes = gui_output_path.read_bytes()
    finally:
        _uninstall()

    assert gui_bytes == cli_bytes
