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

import asyncio
import importlib
import sys
import types
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
            input_path=str(tracklist),
            name="MyList",
            output_dir="",
            playlist_folder="",
            allow_unmatched=False,
            full_collection=False,
        )
        with patch("uuid.uuid4", return_value=_FIXED_UUID):
            gui_result, _read = app._run_build_playlist(inputs)
        assert gui_result.output is not None, gui_result.errors
        # _run_build_playlist writes the file itself, at the path
        # _derive_build_playlist_output_path derives from the output
        # folder and the name (DL-272, DL-297) - with no output folder
        # chosen, base's own directory.
        gui_output_path = app._derive_build_playlist_output_path(base, "", "MyList")
        gui_bytes = gui_output_path.read_bytes()
    finally:
        _uninstall()

    assert gui_bytes == cli_bytes


def _gui_run(base: Path, input_path: Path, name: str) -> tuple[bytes, object]:
    """The GUI write path over one input, with no output folder and no
    playlist folder chosen: the file lands beside base."""
    _uninstall()
    _install_nicegui_stub()
    try:
        app = importlib.import_module("traktor_nml.gui.app")
        inputs = app.FormInputs(
            base_path=str(base), input_path=str(input_path), name=name,
            output_dir="", playlist_folder="", allow_unmatched=False, full_collection=False,
        )
        with patch("uuid.uuid4", return_value=_FIXED_UUID):
            result, read = app._run_build_playlist(inputs)
        assert result.output is not None, result.errors
        return app._derive_build_playlist_output_path(base, "", name).read_bytes(), read
    finally:
        _uninstall()


def _write_csv(tmp_path: Path) -> Path:
    listing = tmp_path / "list.csv"
    listing.write_text("Artist,Title\nA,One\nB,Two\n", encoding="utf-8")
    return listing


def _write_m3u(tmp_path: Path) -> Path:
    listing = tmp_path / "set.m3u8"
    music = tmp_path / "Music" / "Set"
    listing.write_text(f"{music / '1 - one.mp3'}\n{music / '2 - two.mp3'}\n", encoding="utf-8")
    return listing


def _write_folder(tmp_path: Path) -> Path:
    return tmp_path / "Music" / "Set"


@pytest.mark.parametrize(
    ("make_input", "expected_format"),
    [(_write_csv, "csv"), (_write_m3u, "m3u"), (_write_folder, "folder")],
    ids=["csv", "m3u", "folder"],
)
def test_gui_write_path_matches_cli_for_each_input_format(tmp_path: Path, make_input, expected_format) -> None:
    """For a CSV, an M3U8 and a folder of audio files, the GUI's
    _run_build_playlist and the CLI write byte-identical files, and the
    GUI's run hands back the InputRead naming the format it read
    (DL-262, DL-281, DL-296). Two files sit at their collection
    locations and a third collection entry is named by no input, so the
    isolation pass has something to drop.

    Mutation: _run_build_playlist reads the input through
        playlistinput.read_text in place of playlistinput.read_input, so
        every format is read as a plain track list.
    Observed:
        E           AssertionError: ['unresolved_tracks']
        E           assert None is not None
        E            +  where None = BuildPlaylistResult(output=None, stats={'lines_read': 3, 'lines_resolved': 0, 'unresolved_unparseable': 3, 'unresolved...UnresolvedRow(line_number=3, raw_text='B,Two', artist='', title='', kind='unparseable')], errors=['unresolved_tracks']).output
        E           AssertionError: ['unresolved_tracks']
        E           assert None is not None
        E            +  where None = BuildPlaylistResult(output=None, stats={'lines_read': 2, 'lines_resolved': 0, 'unresolved_unparseable': 0, 'unresolved...80\\test_gui_write_path_matches_cl1\\Music\\Set\\2', title='two.mp3', kind='unmatched')], errors=['unresolved_tracks']).output
        E           AssertionError: ['input_not_found=C:/Users/marcu/AppData/Local/Temp/pytest-of-marcu/pytest-1380/test_gui_write_path_matches_cl2/Music/Set']
        E           assert None is not None
        E            +  where None = BuildPlaylistResult(output=None, stats={}, unresolved_rows=[], errors=['input_not_found=C:/Users/marcu/AppData/Local/Temp/pytest-of-marcu/pytest-1380/test_gui_write_path_matches_cl2/Music/Set']).output
    """
    from tests.test_build_playlist_inputs import _entry_for, _nml as _inputs_nml

    music = tmp_path / "Music" / "Set"
    music.mkdir(parents=True)
    one = music / "1 - one.mp3"
    two = music / "2 - two.mp3"
    for track in (one, two):
        track.write_bytes(b"\0" * 4096)
    lib = tmp_path / "lib"
    lib.mkdir()
    base = lib / "base.nml"
    base.write_text(
        _inputs_nml([
            _entry_for(one, "A", "One", size_kb="4"),
            _entry_for(two, "B", "Two", size_kb="4"),
            _entry_for(tmp_path / "Music" / "Other" / "three.mp3", "C", "Three", size_kb="4"),
        ]),
        encoding="utf-8",
        newline="",
    )
    input_path = make_input(tmp_path)

    cli_out = tmp_path / "cli.nml"
    with patch("uuid.uuid4", return_value=_FIXED_UUID):
        cli = run_tool(
            ["build-playlist", str(base), str(input_path), str(cli_out), "--name", "MyList"],
            cwd=tmp_path,
        )
    assert cli.exit_code == 0, cli.stderr
    assert "entries_written=2" in cli.stdout

    gui_bytes, read = _gui_run(base, input_path, "MyList")
    assert read.format.value == expected_format
    assert gui_bytes == cli_out.read_bytes()


def test_native_template_goes_through_the_save_dialog(tmp_path: Path) -> None:
    """In the native window the template is written through the SAVE
    dialog's path, never ui.download, which pywebview blocks (DL-295).
    The bytes on disk are csv_template_bytes() exactly.

    Mutation: _deliver_csv_template calls ui.download(data,
        CSV_TEMPLATE_FILENAME) and returns in both branches.
    Observed:
        E           AssertionError: assert 1 == 0
        E            +  where 1 = <MagicMock id='2262668074960'>.call_count
    """
    from traktor_nml.playlistinput import csv_template_bytes

    target = tmp_path / "t.csv"
    _uninstall()
    _install_nicegui_stub()
    try:
        app = importlib.import_module("traktor_nml.gui.app")

        async def _io_bound(func, *args):
            return func(*args)

        download = MagicMock()
        save = AsyncMock(return_value=target)
        with patch.object(app, "native_window", return_value=object()), \
                patch.object(app, "pick_save_path", save), \
                patch.object(app.run, "io_bound", _io_bound), \
                patch.object(app.ui, "download", download, create=True):
            asyncio.run(app._deliver_csv_template())
        assert download.call_count == 0
        assert save.await_args.kwargs["save_filename"] == "playlist-template.csv"
        assert target.read_bytes() == csv_template_bytes()
    finally:
        _uninstall()


def test_served_template_goes_through_ui_download() -> None:
    """Served over HTTP, with no native window, the template goes to the
    browser through ui.download with csv_template_bytes() and no SAVE
    dialog is asked for (DL-295).

    Mutation: _deliver_csv_template tests `if window is not None:` in
        place of `if window is None:`, so the served page asks for a
        SAVE dialog it has no window for.
    Observed:
        E           AssertionError: assert 1 == 0
        E            +  where 1 = <AsyncMock id='2260129914832'>.await_count
    """
    from traktor_nml.playlistinput import csv_template_bytes

    _uninstall()
    _install_nicegui_stub()
    try:
        app = importlib.import_module("traktor_nml.gui.app")
        download = MagicMock()
        save = AsyncMock(return_value=None)
        with patch.object(app, "native_window", return_value=None), \
                patch.object(app, "pick_save_path", save), \
                patch.object(app.ui, "download", download, create=True):
            asyncio.run(app._deliver_csv_template())
        assert save.await_count == 0
        download.assert_called_once_with(csv_template_bytes(), "playlist-template.csv")
    finally:
        _uninstall()
