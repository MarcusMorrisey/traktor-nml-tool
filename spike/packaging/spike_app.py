"""Throwaway NiceGUI app for the docs/nicegui-gui-analysis.md section 6 spike.

Not part of the tool. It exists to answer the eight packaging checks that
block the distribution section, and it is committed rather than discarded
because checks 4 and 5 must be run on a clean Windows 11 machine with no
Python installed - which is not the machine that wrote it.

Run from source:   python spike/packaging/spike_app.py
Build:             see spike/packaging/build.sh
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from nicegui import app, native, ui

from checks import find_fpcalc, frozen_root, state_dir

@ui.page("/")
def index() -> None:
    ui.label("section 6 packaging spike").classes("text-xl font-bold")
    ui.label(f"frozen: {frozen_root() or 'no (running from source)'}")
    ui.label(f"state dir (check 6): {state_dir()}")
    ui.label(f"cold start (check 4): {time.time() - LAUNCHED_AT:.1f}s to first page render")
    out = ui.log().classes("w-full h-64")

    def check_lxml() -> None:
        """Check 1: lxml binaries survive bundling, on the real 11.7MB file."""
        try:
            from lxml import etree
        except Exception as exc:
            out.push(f"CHECK 1 lxml  FAIL import: {exc!r}")
            return
        target = Path(os.environ.get("SPIKE_NML", "collection_textual_patch_test.nml"))
        if not target.exists():
            out.push(f"CHECK 1 lxml  SKIP: {target} not found (set SPIKE_NML)")
            return
        started = time.time()
        root = etree.parse(str(target)).getroot()
        entries = root.findall(".//COLLECTION/ENTRY")
        out.push(f"CHECK 1 lxml  PASS: {len(entries)} entries in {time.time() - started:.1f}s")

    def check_fpcalc() -> None:
        """Check 2: bundled fpcalc is locatable and executable."""
        binary = find_fpcalc()
        if binary is None:
            out.push("CHECK 2 fpcalc  FAIL: not found (bundled copy missing)")
            return
        try:
            done = subprocess.run([str(binary), "-version"], capture_output=True, text=True, timeout=10)
        except Exception as exc:
            out.push(f"CHECK 2 fpcalc  FAIL running {binary}: {exc!r}")
            return
        verdict = "PASS" if done.returncode == 0 else f"FAIL rc={done.returncode}"
        out.push(f"CHECK 2 fpcalc  {verdict}: {binary} -> {done.stdout.strip()[:60]}")

    async def check_dialog() -> None:
        """Check 3: native file and directory dialogs return real paths."""
        try:
            picked = await app.native.main_window.create_file_dialog(allow_multiple=False)
            out.push(f"CHECK 3 file dialog  PASS: {picked}")
            folder = await app.native.main_window.create_file_dialog(dialog_type=20)  # FOLDER_DIALOG
            out.push(f"CHECK 3 dir dialog   PASS: {folder}")
        except Exception as exc:
            out.push(f"CHECK 3 dialogs  FAIL: {exc!r}")

    def check_state() -> None:
        """Check 6/7: the state directory is writable and survives a rerun."""
        marker = state_dir() / "spike-marker.txt"
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            previous = marker.read_text(encoding="utf-8") if marker.exists() else "(none)"
            marker.write_text(f"written {time.time():.0f}", encoding="utf-8")
            out.push(f"CHECK 6/7 state  PASS: {marker}\n           previous run left: {previous}")
        except Exception as exc:
            out.push(f"CHECK 6/7 state  FAIL: {exc!r}")

    with ui.row():
        ui.button("1. lxml + 11.7MB parse", on_click=check_lxml)
        ui.button("2. bundled fpcalc", on_click=check_fpcalc)
        ui.button("3. native dialogs", on_click=check_dialog)
        ui.button("6/7. persistent state", on_click=check_state)


# reload=False and an explicitly-found free port are both required for a
# packaged build (nicegui-pack --help states this); without the port the
# bundled app can collide with whatever is already on the default.
ui.run(
    native=True,
    reload=False,
    port=native.find_open_port(),
    title="packaging spike",
    window_size=(900, 640),
)
