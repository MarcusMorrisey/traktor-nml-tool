"""Guards traktor_nml/gui/_fs_nav.py, the pure path arithmetic behind
LocalFilePicker's drive navigation. Constructs each broken scenario in
executable code and records the mutation made and the output observed,
matching the register tests/test_scan_diagnostics.py,
tests/test_review_channel.py, tests/test_reconnect_write_core.py,
tests/test_gui_wizard_state.py and
tests/test_gui_file_picker_native_detection.py already use.

The bug this exists to catch: LocalFilePicker started at the process
CWD's drive and had no route to any other drive - ".." at a drive root
is a dead control (Path("C:/").parent is Path("C:/") on Windows) and
nothing enumerated other drives, so "D:" was unreachable by any
navigation the dialog offered ("I can't reach D: from the choose
collection file").

_fs_nav.py imports neither nicegui nor webview, so this suite reaches
it directly on the pytest interpreter, which has neither installed
(docs/nicegui-gui-analysis.md #5) - no sys.modules stub is needed here,
unlike tests/test_gui_file_picker_native_detection.py's file_picker.py
guard.

PureWindowsPath is used throughout instead of Path so the drive-root
scenarios ("C:/".parent == "C:/") are exercised identically regardless
of which OS runs the suite: PureWindowsPath applies Windows path rules
without touching the filesystem, and every function under test here
(parent_target, resolve_target, entries_for's DRIVE_LIST branch) only
calls .parent, equality, and the / operator - never a filesystem
method - so a Pure path satisfies it exactly like a real one would.
"""

from __future__ import annotations

from pathlib import PureWindowsPath

from traktor_nml.gui import _fs_nav


def test_drive_root_dotdot_leads_to_drive_list_not_itself() -> None:
    """At a drive root with more than one drive available, ".." must
    lead to DRIVE_LIST rather than back to the root itself.

    Observed to fail against the pre-fix logic: the original
    `_on_double_click` computed `self.path = self.path.parent`
    unconditionally. Reproduced below directly - naive_target is
    PureWindowsPath('C:/'), equal to the starting root - confirming
    that step is a dead control: the row renders, but clicking it
    leaves the location unchanged. The fixed parent_target instead
    returns DRIVE_LIST.
    """
    root = PureWindowsPath("C:/")
    drive_roots = [PureWindowsPath("C:/"), PureWindowsPath("D:/")]

    naive_target = root.parent
    assert naive_target == root, "reproduced: naive '..' at a drive root goes nowhere"

    fixed_target = _fs_nav.parent_target(root, drive_roots)
    assert fixed_target == _fs_nav.DRIVE_LIST


def test_single_drive_root_dotdot_target_is_none_not_a_dead_entry(tmp_path) -> None:
    """With zero or one drive available (POSIX's single root, or a
    single-drive Windows machine), there is nowhere for ".." to lead -
    parent_target returns None so entries_for omits the row instead of
    rendering a control that does nothing when clicked."""
    root = PureWindowsPath("C:/")
    assert _fs_nav.parent_target(root, [PureWindowsPath("C:/")]) is None
    assert _fs_nav.parent_target(root, []) is None

    # entries_for calls .iterdir() on a real directory branch, so this
    # part uses the real filesystem root of tmp_path (a genuine Path,
    # not PureWindowsPath) with itself as the sole "drive".
    real_root = tmp_path.anchor and type(tmp_path)(tmp_path.anchor) or tmp_path
    rows = _fs_nav.entries_for(real_root, [real_root])
    assert all(row["name"] != ".." for row in rows), "dead '..' row must not render"


def test_drive_list_entries_expose_every_drive() -> None:
    """entries_for(DRIVE_LIST, ...) renders one row per probed drive -
    the listing ".." at a multi-drive root leads to."""
    drive_roots = [PureWindowsPath("C:/"), PureWindowsPath("D:/")]
    rows = _fs_nav.entries_for(_fs_nav.DRIVE_LIST, drive_roots)
    assert {row["name"] for row in rows} == {"C:/", "D:/"}


def test_full_navigation_reaches_a_different_drive() -> None:
    """resolve_target - the one computation both _on_double_click and
    _select call - carries a location from C:/ to D:/ through the
    picker's own navigation: '..' first (to DRIVE_LIST), then "D:/".
    This is the concrete reachability property the bug report names.

    Observed to fail against the pre-fix picker: there was no
    equivalent of the first step at all (".." mapped straight back to
    C:/ per the test above), so no sequence of clicks reached D:/.
    """
    location: _fs_nav.Location = PureWindowsPath("C:/")
    drive_roots = [PureWindowsPath("C:/"), PureWindowsPath("D:/")]

    location = _fs_nav.resolve_target(location, "..", drive_roots)
    assert location == _fs_nav.DRIVE_LIST

    location = _fs_nav.resolve_target(location, "D:/", drive_roots)
    assert location == PureWindowsPath("D:/")


def test_drive_list_has_no_dotdot_of_its_own() -> None:
    """DRIVE_LIST is the top of this picker's navigation: no ".." row
    renders there, and asking resolve_target for one anyway returns
    None rather than a bogus target."""
    drive_roots = [PureWindowsPath("C:/"), PureWindowsPath("D:/")]
    rows = _fs_nav.entries_for(_fs_nav.DRIVE_LIST, drive_roots)
    assert all(row["name"] != ".." for row in rows)
    assert _fs_nav.resolve_target(_fs_nav.DRIVE_LIST, "..", drive_roots) is None


def test_list_drive_roots_is_posix_safe() -> None:
    """On a non-Windows os.name, list_drive_roots returns [] without
    running the Windows-only drive-letter probe at all.

    Observed: monkeypatching _fs_nav.os.name to "posix" makes
    list_drive_roots() return [] even on this (Windows) test machine,
    where real drive letters exist - proving the os.name check
    short-circuits before any Path(f"{letter}:/").exists() call, so
    the probe cannot run on POSIX where there is one root."""
    original_name = _fs_nav.os.name
    _fs_nav.os.name = "posix"
    try:
        assert _fs_nav.list_drive_roots() == []
    finally:
        _fs_nav.os.name = original_name


def test_list_drive_roots_returns_only_letters_that_exist(monkeypatch) -> None:
    """On os.name == "nt", list_drive_roots probes each of the 26
    letters and keeps only the ones that exist - verified by faking
    Path.exists() to answer True for C: and D: only, and asserting the
    other 24 letters are absent from the result.

    Observed: with exists() faked this way, list_drive_roots() returns
    exactly {"C:", "D:"} - not all 26, and not the real drives this
    machine happens to have."""
    monkeypatch.setattr(_fs_nav.os, "name", "nt")

    def fake_exists(self):
        return self.drive in ("C:", "D:")

    monkeypatch.setattr(_fs_nav.Path, "exists", fake_exists, raising=False)

    roots = _fs_nav.list_drive_roots()
    assert {root.drive for root in roots} == {"C:", "D:"}
