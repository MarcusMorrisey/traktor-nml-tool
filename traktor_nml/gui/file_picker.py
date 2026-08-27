"""Server-side selection of the collection file and the scan roots.

Scan roots are directories on the machine holding the music library, and
the collection file is a specific .nml path on that same machine - both
must be named on the server's filesystem, not uploaded to it. ui.upload
is a browser upload that moves bytes to the server and has no directory
form at all, so it is the wrong shape here (docs/nicegui-gui-analysis.md
#4, "File selection").

In native mode (ui.run(native=True)) pywebview owns the window and offers
a real OS file dialog through create_file_dialog. Outside native mode -
ui.run(show=True) opening a browser - there is no server-side dialog to
call, so this module falls back to NiceGUI's local_file_picker component
pattern, a small ui.dialog listing the server's own filesystem.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import webview
from nicegui import app, events, ui


def pick_file(*, start_dir: Optional[Path] = None) -> Optional[Path]:
    """One existing file, chosen through pywebview's native dialog in
    native mode."""
    windows = webview.windows
    if not windows:
        return None
    result = windows[0].create_file_dialog(
        webview.FileDialog.OPEN,
        directory=str(start_dir) if start_dir is not None else "",
        allow_multiple=False,
    )
    if not result:
        return None
    return Path(result[0])


def pick_folder(*, start_dir: Optional[Path] = None) -> Optional[Path]:
    """One existing directory, chosen through pywebview's native
    dialog in native mode."""
    windows = webview.windows
    if not windows:
        return None
    result = windows[0].create_file_dialog(
        webview.FileDialog.FOLDER,
        directory=str(start_dir) if start_dir is not None else "",
    )
    if not result:
        return None
    return Path(result[0])


class LocalFilePicker(ui.dialog):
    """A minimal server-filesystem browser, offered when no native
    window is available to host pywebview's dialog - the local_file_picker
    component pattern #4 names. Lists directories and files under one
    directory at a time; selecting a file closes the dialog with that
    path, and ".." navigates to the parent directory."""

    def __init__(self, directory: str = ".", *, upper_limit: Optional[str] = None,
                 show_hidden_files: bool = False, directories_only: bool = False) -> None:
        super().__init__()
        self.path = Path(directory).expanduser().resolve()
        self.upper_limit = None if upper_limit is None else Path(upper_limit).expanduser().resolve()
        self.show_hidden_files = show_hidden_files
        self.directories_only = directories_only

        with self, ui.card():
            self.add_slot("header")
            self.grid = ui.aggrid({
                "columnDefs": [{"field": "name", "headerName": "Name"}],
                "rowSelection": "single",
            }, html_columns=[0]).classes("w-96").on("cellDoubleClicked", self._on_double_click)
            with ui.row().classes("justify-end w-full"):
                ui.button("Cancel", on_click=self.close)
                ui.button("Select", on_click=self._select)
        self._update_grid()

    def _entries(self) -> list[dict]:
        entries = []
        if self.upper_limit is None or self.path != self.upper_limit:
            entries.append({"name": ".."})
        try:
            children = sorted(self.path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            children = []
        for child in children:
            if not self.show_hidden_files and child.name.startswith("."):
                continue
            if self.directories_only and not child.is_dir():
                continue
            entries.append({"name": (child.name + "/") if child.is_dir() else child.name})
        return entries

    def _update_grid(self) -> None:
        self.grid.options["rowData"] = self._entries()
        self.grid.update()

    def _on_double_click(self, event: events.GenericEventArguments) -> None:
        name = event.args["data"]["name"]
        if name == "..":
            self.path = self.path.parent
        else:
            self.path = self.path / name.rstrip("/")
        if self.path.is_dir():
            self._update_grid()
        else:
            self.submit([str(self.path)])

    def _select(self) -> None:
        rows = self.grid.selected_rows if hasattr(self.grid, "selected_rows") else []
        if not rows:
            self.submit([str(self.path)])
            return
        name = rows[0]["name"]
        target = self.path if name == ".." else self.path / name.rstrip("/")
        self.submit([str(target)])


async def pick_file_or_folder(*, native: bool, start_dir: Optional[Path] = None,
                               directories_only: bool = False) -> Optional[Path]:
    """The one entry point app.py calls: native mode reaches pywebview's
    create_file_dialog directly, otherwise a LocalFilePicker dialog is
    shown and awaited."""
    if native:
        return pick_folder(start_dir=start_dir) if directories_only else pick_file(start_dir=start_dir)
    picker = LocalFilePicker(str(start_dir) if start_dir is not None else ".", directories_only=directories_only)
    result = await picker
    if not result:
        return None
    return Path(result[0])
