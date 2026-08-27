"""Pure filesystem-navigation arithmetic for LocalFilePicker: drive
enumeration, and the single computation of what a row name ("..", a
child, or a drive) resolves to. No nicegui or webview import, so this
module is reachable directly by the pytest interpreter, which has
neither installed (docs/nicegui-gui-analysis.md #5) - the navigation
logic does not need to be exercised through file_picker.py's stubbed
imports at all.

DRIVE_LIST is the sentinel Location meaning "the virtual listing of
every drive", distinct from any real Path. LocalFilePicker's ".."
control at an ordinary drive root (Path.parent == Path itself, so a
plain path.parent step goes nowhere) leads here when more than one
drive is available - the mechanism that makes a second drive (D:, a
mapped network drive, ...) reachable through the picker's own
navigation instead of only through the drive it started on.
"""

from __future__ import annotations

import os
import string
from pathlib import Path
from typing import List, Optional, Union

DRIVE_LIST = "__DRIVE_LIST__"
Location = Union[Path, str]


def list_drive_roots() -> List[Path]:
    """Every local drive root reachable from this process.

    POSIX has a single root already reachable as the ordinary directory
    tree (`/`), so this returns an empty list there, detected via
    os.name rather than assuming Windows - the Windows-only letter
    probe below never runs on POSIX.

    On Windows probes each of the 26 possible drive letters with
    Path(f"{letter}:/").exists(). This runs once per LocalFilePicker
    dialog, from __init__ - not once per grid render - so a slow or
    disconnected mapped network drive blocking on .exists() can stall
    opening the dialog, but not every subsequent navigation click. That
    bounded, one-time cost is judged acceptable here; probing on every
    render would multiply it by every ".." and directory click instead.
    """
    if os.name != "nt":
        return []
    return [
        Path(f"{letter}:/")
        for letter in string.ascii_uppercase
        if Path(f"{letter}:/").exists()
    ]


def is_drive_root(path: Path) -> bool:
    """True at a filesystem root such as C:/ or / - the condition under
    which Path.parent equals the path itself, and so under which a
    plain path.parent step is a dead control."""
    return path.parent == path


def parent_target(path: Path, drive_roots: List[Path]) -> Optional[Location]:
    """What ".." should navigate to from `path`.

    - Not a drive root: the ordinary parent directory.
    - A drive root with more than one drive available: DRIVE_LIST, so
      ".." leads to a place every other drive is reachable from,
      instead of looping back to `path` itself.
    - A drive root with zero or one drive available (POSIX, or a
      single-drive Windows machine): None. There is nowhere for ".."
      to go, and callers must omit the entry rather than render a
      dead control.
    """
    if not is_drive_root(path):
        return path.parent
    if len(drive_roots) > 1:
        return DRIVE_LIST
    return None


def resolve_target(location: Location, name: str, drive_roots: List[Path]) -> Optional[Location]:
    """The Location a row named `name` resolves to from the current
    `location` - the one computation both _on_double_click and _select
    call, so the two handlers cannot recognize a new kind of entry
    differently from each other.

    From DRIVE_LIST, `name` is a drive's own rendered name (e.g.
    "C:/") and resolves to that Path directly; DRIVE_LIST has no
    filesystem parent of its own, so a ".." row is never rendered
    there and this returns None if asked anyway. From an ordinary
    directory, ".." resolves through parent_target; any other name is
    a child of `location`.
    """
    if location == DRIVE_LIST:
        if name == "..":
            return None
        return Path(name)
    if name == "..":
        return parent_target(location, drive_roots)
    return location / name.rstrip("/")


def entries_for(location: Location, drive_roots: List[Path], *, upper_limit: Optional[Path] = None,
                 show_hidden_files: bool = False, directories_only: bool = False) -> List[dict]:
    """The grid rows for `location`.

    When location is DRIVE_LIST: one row per probed drive, and nothing
    else - DRIVE_LIST is the top of this picker's navigation, so no
    ".." row is rendered above it.

    Otherwise: a ".." row - per parent_target, omitted both when
    location == upper_limit (the existing limit) and when
    parent_target returns None (a single-drive root, or POSIX '/')
    since that is a dead control - followed by location's children.
    """
    if location == DRIVE_LIST:
        return [{"name": root.as_posix()} for root in drive_roots]

    entries: List[dict] = []
    at_limit = upper_limit is not None and location == upper_limit
    if not at_limit and parent_target(location, drive_roots) is not None:
        entries.append({"name": ".."})
    try:
        children = sorted(location.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        children = []
    for child in children:
        if not show_hidden_files and child.name.startswith("."):
            continue
        if directories_only and not child.is_dir():
            continue
        entries.append({"name": (child.name + "/") if child.is_dir() else child.name})
    return entries
