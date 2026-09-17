"""The build-playlist screen's two folders never share a value (DL-297):
the output folder decides where the .nml is written on disk, and the
playlist folder decides where the playlist sits in the collection.

Importing traktor_nml.gui.app needs nicegui; the stand-ins from
tests/test_build_playlist_byte_identity.py are installed per test and
removed in a finally. The page's own wiring is read from app.py as an
AST, never imported, because the page body runs only under a real
NiceGUI client.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path
from unittest.mock import patch

from tests.conftest import run_tool
from tests.test_build_playlist_byte_identity import _FIXED_UUID, _entry, _install_nicegui_stub, _uninstall

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def _app():
    _uninstall()
    _install_nicegui_stub()
    return importlib.import_module("traktor_nml.gui.app")


def test_output_path_with_and_without_an_output_folder(tmp_path: Path) -> None:
    """No output folder writes beside the base collection; a chosen one
    writes <folder>/<name>.nml. The function has no playlist-folder
    parameter at all.

    Mutation: _derive_build_playlist_output_path takes a fourth
        playlist_folder parameter and joins it onto the directory, so
        its parameter list is not ['base_path', 'output_dir', 'name'].
    Observed:
        E           AssertionError: assert ['base_path',...ylist_folder'] == ['base_path',..._dir', 'name']
        E
        E             Left contains one more item: 'playlist_folder'
        E             Use -v to get more diff
    """
    try:
        app = _app()
        base = tmp_path / "lib" / "collection.nml"
        assert app._derive_build_playlist_output_path(base, "", "Set") == tmp_path / "lib" / "Set.nml"
        chosen = tmp_path / "exports"
        assert app._derive_build_playlist_output_path(base, str(chosen), "Set") == chosen / "Set.nml"
        params = list(inspect.signature(app._derive_build_playlist_output_path).parameters)
        assert params == ["base_path", "output_dir", "name"]
    finally:
        _uninstall()


def _base_with_folder() -> str:
    entries = _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="2">{entries}</COLLECTION>'
        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="1">'
        '<NODE TYPE="FOLDER" NAME="Sets"><SUBNODES COUNT="0"></SUBNODES></NODE>'
        "</SUBNODES></NODE></PLAYLISTS><SETS></SETS><INDEXING></INDEXING></NML>"
    )


def test_output_folder_and_playlist_folder_match_the_cli(tmp_path: Path) -> None:
    """Choosing output folder X and playlist folder Sets writes
    X/<name>.nml with the playlist under FOLDER Sets, byte-identical to
    the CLI run with output X/<name>.nml and --target-folder Sets.

    Mutation: _run_build_playlist passes inputs.output_dir as
        target_folder, so the run refuses with target_folder_not_found
        and result.errors is not empty.
    Observed:
        E           AssertionError: assert ['target_folder_not_found'] == []
        E
        E             Left contains one more item: 'target_folder_not_found'
        E             Use -v to get more diff
    """
    base = tmp_path / "base.nml"
    base.write_text(_base_with_folder(), encoding="utf-8", newline="")
    tracks = tmp_path / "tracks.txt"
    tracks.write_text("A - One\nB - Two\n", encoding="utf-8")
    cli_dir = tmp_path / "cli"
    gui_dir = tmp_path / "gui"
    cli_dir.mkdir()
    gui_dir.mkdir()

    with patch("uuid.uuid4", return_value=_FIXED_UUID):
        cli = run_tool(
            ["build-playlist", str(base), str(tracks), str(cli_dir / "Set.nml"), "--name", "Set",
             "--target-folder", "Sets", "--full-collection"],
            cwd=tmp_path,
        )
    assert cli.exit_code == 0, cli.stderr

    try:
        app = _app()
        inputs = app.FormInputs(
            base_path=str(base), input_path=str(tracks), name="Set",
            output_dir=str(gui_dir), playlist_folder="Sets",
            allow_unmatched=False, full_collection=True,
        )
        with patch("uuid.uuid4", return_value=_FIXED_UUID):
            result, _read = app._run_build_playlist(inputs)
        assert result.errors == []
    finally:
        _uninstall()

    gui_bytes = (gui_dir / "Set.nml").read_bytes()
    assert gui_bytes == (cli_dir / "Set.nml").read_bytes()
    # --full-collection keeps the tree, so the placement is visible: the
    # playlist is Sets' child, not $ROOT's.
    from traktor_nml.xmlio import parse_xml_bytes

    sets = parse_xml_bytes(gui_bytes).find(".//PLAYLISTS/NODE/SUBNODES/NODE[@NAME='Sets']")
    assert [node.attrib.get("NAME") for node in sets.find("SUBNODES")] == ["Set"]
    assert not (tmp_path / "Sets").exists()


def _page_function() -> ast.FunctionDef:
    tree = ast.parse(_APP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_playlist_page":
            return node
    raise AssertionError("app.py defines no build_playlist_page")


def _inner(page: ast.FunctionDef, name: str) -> ast.FunctionDef:
    for node in ast.walk(page):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"build_playlist_page defines no {name}")


def _calls(node: ast.AST) -> list[str]:
    """Every call's dotted name under node, e.g.
    'buildplaylist_view.effective_playlist_folder'."""
    names = []
    for call in ast.walk(node):
        if isinstance(call, ast.Call):
            names.append(ast.unparse(call.func))
    return names


def test_the_page_gates_the_playlist_folder_on_full_collection() -> None:
    """The page composes the chooser-gating rule rather than holding it
    beside the page: the value the run receives as playlist_folder goes
    through buildplaylist_view.effective_playlist_folder with the Full
    collection switch's value, the switch's own on_change re-syncs the
    chooser, and the page build syncs it once so its first paint is the
    disabled state. A guard reading effective_playlist_folder alone is
    green while the page never calls it (DL-189, DL-297).

    Mutation: _current_inputs passes
        playlist_folder=playlist_folder_select.value or "" in place of
        playlist_folder=_selected_playlist_folder(), so a folder chosen
        with Full collection on and left selected reaches the run after
        the switch is turned off.
    Observed:
        E       assert "playlist_fol...t.value or ''" == '_selected_playlist_folder()'
        E
        E         - _selected_playlist_folder()
        E         + playlist_folder_select.value or ''

    Mutation: the page build's closing _sync_playlist_folder() call is
        deleted, so the chooser paints enabled with Full collection off
        until the switch is first touched.
    Observed:
        E       AssertionError: assert '_sync_playlist_folder' in ['_refresh_write_button', '_show_output_dir']
    """
    page = _page_function()

    current = _inner(page, "_current_inputs")
    form = next(
        call for call in ast.walk(current)
        if isinstance(call, ast.Call) and ast.unparse(call.func) == "FormInputs"
    )
    playlist_folder = {kw.arg: ast.unparse(kw.value) for kw in form.keywords}["playlist_folder"]
    assert playlist_folder == "_selected_playlist_folder()"

    selected = _inner(page, "_selected_playlist_folder")
    gate = next(
        call for call in ast.walk(selected)
        if isinstance(call, ast.Call)
        and ast.unparse(call.func) == "buildplaylist_view.effective_playlist_folder"
    )
    assert ast.unparse(gate.args[0]) == "bool(full_collection_switch.value)"

    sync = _inner(page, "_sync_playlist_folder")
    assert "playlist_folder_select.set_enabled" in _calls(sync)
    assert "playlist_folder_note.set_visibility" in _calls(sync)

    switch = next(
        call for call in ast.walk(page)
        if isinstance(call, ast.Call)
        and ast.unparse(call.func) == "ui.switch"
        and call.args
        and ast.unparse(call.args[0]) == "buildplaylist_view.FULL_COLLECTION_LABEL"
    )
    on_change = {kw.arg: kw.value for kw in switch.keywords}["on_change"]
    assert "_sync_playlist_folder" in _calls(on_change)

    top_level_calls = [
        ast.unparse(stmt.value.func) for stmt in page.body
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
    ]
    assert "_sync_playlist_folder" in top_level_calls
