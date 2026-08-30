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

pick_file_or_folder detects which of those two situations applies by
reading nicegui.app.native.main_window, rather than trusting a
caller-supplied flag - so app.py never has to know or assert whether it
is running natively.

That attribute is the signal because NiceGUI runs pywebview in a
separate spawned process (nicegui/native/native_mode.py builds its
window inside SPAWN_CONTEXT.Process), so `webview.windows` is empty in
the server process that handles the click no matter whether a native
window exists. What the server process holds instead is
app.native.main_window, a WindowProxy whose create_file_dialog
(nicegui/native/native.py) marshals the call across that process
boundary and is awaitable rather than blocking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import webview
from nicegui import app, events, ui

from ._fs_nav import DRIVE_LIST, entries_for, list_drive_roots, resolve_target


def native_window():
    """The WindowProxy for the pywebview window, or None when the app is
    served over HTTP with no native window behind it.

    The single place this module decides what "native" means. Reads
    nicegui.app.native.main_window rather than webview.windows: the
    window is built in a separate spawned process, so webview.windows is
    empty here in both configurations and cannot tell them apart."""
    return getattr(app.native, "main_window", None)


async def pick_file(window, *, start_dir: Optional[Path] = None) -> Optional[Path]:
    """One existing file, chosen through pywebview's native dialog in
    native mode. Awaits `window`, a WindowProxy, because the dialog it
    opens lives in the window's own process."""
    result = await window.create_file_dialog(
        webview.FileDialog.OPEN,
        directory=str(start_dir) if start_dir is not None else "",
        allow_multiple=False,
    )
    if not result:
        return None
    return Path(result[0])


async def pick_folder(window, *, start_dir: Optional[Path] = None) -> Optional[Path]:
    """One existing directory, chosen through pywebview's native
    dialog in native mode. Awaits `window` for the same reason
    pick_file does."""
    result = await window.create_file_dialog(
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
    path, and ".." navigates to the parent directory.

    Every probed drive is reachable, not only the one this dialog
    started on: at a drive root with more than one drive available,
    ".." leads to a virtual drive-list entry (self.path becomes
    traktor_nml.gui._fs_nav.DRIVE_LIST) instead of looping back to the
    root itself, and that listing's rows are the drives themselves.
    With zero or one drive available, ".." is omitted there instead of
    rendering a control that would go nowhere."""

    def __init__(self, directory: str = ".", *, upper_limit: Optional[str] = None,
                 show_hidden_files: bool = False, directories_only: bool = False) -> None:
        super().__init__()
        self.path = Path(directory).expanduser().resolve()
        self.upper_limit = None if upper_limit is None else Path(upper_limit).expanduser().resolve()
        self.show_hidden_files = show_hidden_files
        self.directories_only = directories_only
        self._drive_roots = list_drive_roots()

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
        return entries_for(
            self.path, self._drive_roots,
            upper_limit=self.upper_limit,
            show_hidden_files=self.show_hidden_files,
            directories_only=self.directories_only,
        )

    def _update_grid(self) -> None:
        self.grid.options["rowData"] = self._entries()
        self.grid.update()

    def _on_double_click(self, event: events.GenericEventArguments) -> None:
        name = event.args["data"]["name"]
        target = resolve_target(self.path, name, self._drive_roots)
        if target is None:
            return
        self.path = target
        if self.path == DRIVE_LIST or self.path.is_dir():
            self._update_grid()
        else:
            self.submit([str(self.path)])

    def _select(self) -> None:
        rows = self.grid.selected_rows if hasattr(self.grid, "selected_rows") else []
        if not rows:
            if self.path == DRIVE_LIST:
                return
            self.submit([str(self.path)])
            return
        name = rows[0]["name"]
        target = resolve_target(self.path, name, self._drive_roots)
        if target is None:
            return
        if target == DRIVE_LIST:
            self.path = target
            self._update_grid()
            return
        self.submit([str(target)])


async def pick_file_or_folder(*, native: Optional[bool] = None, start_dir: Optional[Path] = None,
                               directories_only: bool = False) -> Optional[Path]:
    """The one entry point app.py calls: native mode reaches pywebview's
    create_file_dialog through the window proxy, otherwise a
    LocalFilePicker dialog is shown and awaited.

    `native` defaults to None, meaning "detect" - callers (app.py) never
    hardcode it, and native_window() is the one place that decides.
    A None window means the app is being served over HTTP with no native
    window to host a dialog in, and the LocalFilePicker fallback is used
    instead.
    """
    window = native_window()
    if native is None:
        native = window is not None
    if native:
        if window is None:
            ui.notify("No native file dialog is available", type="negative")
            return None
        if directories_only:
            return await pick_folder(window, start_dir=start_dir)
        return await pick_file(window, start_dir=start_dir)
    picker = LocalFilePicker(str(start_dir) if start_dir is not None else ".", directories_only=directories_only)
    result = await picker
    if not result:
        return None
    return Path(result[0])
