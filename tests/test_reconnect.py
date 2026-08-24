"""Disk-scan reconnection: one-to-one assignment and volume identity."""

from __future__ import annotations

from pathlib import Path

import pytest

from traktor_nml.fingerprint import HAS_ACOUSTID
from tests.conftest import run_tool


def _write_nml(path: Path, entries_xml: str, entries_count: int = 1) -> None:
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS>'
        "<SETS></SETS><INDEXING></INDEXING></NML>",
        encoding="utf-8",
        newline="",
    )


def _entry(artist, title, volume, dirv, filename, size="16", time="1.0"):
    """Minimal COLLECTION ENTRY carrying only the attributes the
    file/size/time match tiers need; PLAYLISTS/SETS/INDEXING are always
    present but empty so the tool's other schema assumptions still hold."""
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="{dirv}" FILE="{filename}" VOLUME="{volume}" VOLUMEID="{volume}"></LOCATION>'
        f'<INFO BITRATE="320" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
        "</ENTRY>"
    )


def test_scan_reconnect_reports_match_without_writing(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    (music / "xtal.mp3").write_bytes(b"\x00" * 16)

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))

    result = run_tool(
        [
            "scan-reconnect-candidates", str(old_nml),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
            # mutagen is not installed in this test environment, so tags are
            # always empty; filename confidence is required to match at all.
            "--match-confidence", "filename",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert "reconnectable=1" in result.stdout
    assert not (tmp_path / "out.nml").exists()


def test_no_output_assigns_two_entries_the_same_location(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    (music / "track.mp3").write_bytes(b"\x00" * 16)

    old_nml = tmp_path / "old.nml"
    _write_nml(
        old_nml,
        _entry("A", "One", "Z:", "/:gone1/:", "track.mp3") + _entry("A", "One", "Z:", "/:gone2/:", "track.mp3"),
        entries_count=2,
    )

    result = run_tool(
        [
            "rewrite-from-reconnect", str(old_nml), str(tmp_path / "out.nml"),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
            "--match-confidence", "filename",
            "--csv", str(tmp_path / "ambiguous.csv"),
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    # Both old entries claim the one candidate on disk, so both are withdrawn.
    assert "destination_collisions=2" in result.stdout
    out_path = tmp_path / "out.nml"
    if out_path.exists():
        assert 'VOLUME="C:"' not in out_path.read_text(encoding="utf-8")


def test_absent_volume_map_and_ambiguous_prefix_is_hard_error(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    (music / "xtal.mp3").write_bytes(b"\x00" * 16)

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))

    result = run_tool(
        ["scan-reconnect-candidates", str(old_nml), "--scan-root", str(music)],
        cwd=tmp_path,
    )
    assert result.exit_code == 2


def test_dry_run_and_write_agree_on_counts(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    (music / "xtal.mp3").write_bytes(b"\x00" * 16)

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))

    common = [
        "rewrite-from-reconnect", str(old_nml), str(tmp_path / "out.nml"),
        "--scan-root", str(music),
        "--volume-map", str(music), "C:", "C:",
    ]
    dry = run_tool(common + ["--dry-run"], cwd=tmp_path)
    real = run_tool(common, cwd=tmp_path)
    assert dry.stdout.split("output_written")[0] == real.stdout.split("output_written")[0]


@pytest.mark.skipif(HAS_ACOUSTID, reason="exercises the missing-dependency path only")
def test_fingerprint_flag_without_dependency_warns_rather_than_silently_no_ops(tmp_path: Path) -> None:
    """--fingerprint with pyacoustid/fpcalc absent must not silently do
    nothing: the run still completes (the tier just never contributes a
    match), but a diagnostic naming the missing dependency is printed."""
    music = tmp_path / "music"
    music.mkdir()
    (music / "xtal.mp3").write_bytes(b"\x00" * 16)

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))

    result = run_tool(
        [
            "scan-reconnect-candidates", str(old_nml),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
            "--match-confidence", "filename",
            "--fingerprint",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert "fingerprint_dependency_missing" in result.stderr
