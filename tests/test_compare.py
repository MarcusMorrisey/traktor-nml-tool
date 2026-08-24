"""Compare-based rewriting at the CLI level: input protection and the
shared one-to-one assignment guarantee (DL-004, DL-015, DL-016, DL-023)."""

from __future__ import annotations

from pathlib import Path

from traktor_nml.confidence import MatchConfidence
from traktor_nml.matching import match_records
from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.xmlio import ET
from tests.conftest import run_tool


def _nml(entries_xml: str, entries_count: int) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS>'
        '<SETS></SETS><INDEXING></INDEXING></NML>'
    )


def _entry(artist, title, filename, size="16", time="1.0"):
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="/:Music/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
        f'<INFO BITRATE="320" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
        "</ENTRY>"
    )


def test_output_equal_to_new_input_is_refused(tmp_path: Path) -> None:
    old_path = tmp_path / "old.nml"
    old_path.write_text(_nml(_entry("A", "Song", "song.mp3"), 1), encoding="utf-8")
    new_path = tmp_path / "new.nml"
    new_path.write_text(_nml(_entry("A", "Song", "song.mp3"), 1), encoding="utf-8")

    result = run_tool(
        ["rewrite-from-collection-compare", str(old_path), str(new_path), str(new_path)], cwd=tmp_path
    )
    assert result.exit_code == 2
    assert "output_must_differ_from_input" in result.stderr


def test_output_equal_to_old_input_is_refused(tmp_path: Path) -> None:
    old_path = tmp_path / "old.nml"
    old_path.write_text(_nml(_entry("A", "Song", "song.mp3"), 1), encoding="utf-8")
    new_path = tmp_path / "new.nml"
    new_path.write_text(_nml(_entry("A", "Song", "song.mp3"), 1), encoding="utf-8")

    result = run_tool(
        ["rewrite-from-collection-compare", str(old_path), str(new_path), str(old_path)], cwd=tmp_path
    )
    assert result.exit_code == 2
    assert "output_must_differ_from_input" in result.stderr


def test_two_old_entries_matching_one_new_entry_are_both_withdrawn(tmp_path: Path) -> None:
    """Two old entries whose only artist/title/album/time match is one new
    entry both lose their match to the shared post-pass DL-004 already
    enforces for reconnection; the destination collision is reported and
    neither old LOCATION is rewritten."""
    old_path = tmp_path / "old.nml"
    old_path.write_text(
        _nml(
            _entry("A", "Song", "one.mp3", time="100.0") + _entry("A", "Song", "two.mp3", time="100.0"),
            2,
        ),
        encoding="utf-8",
    )
    new_path = tmp_path / "new.nml"
    new_path.write_text(_nml(_entry("A", "Song", "three.mp3", time="100.0"), 1), encoding="utf-8")
    out_path = tmp_path / "out.nml"

    result = run_tool(
        ["rewrite-from-collection-compare", str(old_path), str(new_path), str(out_path)], cwd=tmp_path
    )
    assert result.exit_code == 0
    assert "destination_collisions=2" in result.stdout
    out_text = out_path.read_text(encoding="utf-8")
    assert "one.mp3" in out_text
    assert "two.mp3" in out_text
    assert "three.mp3" not in out_text


def test_stdlib_branch_reports_the_same_destination_collision_stats(tmp_path: Path, monkeypatch) -> None:
    import traktor_nml.rewrite as rewrite_module

    monkeypatch.setattr(rewrite_module, "HAS_LXML", False)

    old_path = tmp_path / "old.nml"
    old_path.write_text(
        _nml(
            _entry("A", "Song", "one.mp3", time="100.0") + _entry("A", "Song", "two.mp3", time="100.0"),
            2,
        ),
        encoding="utf-8",
    )
    new_path = tmp_path / "new.nml"
    new_path.write_text(_nml(_entry("A", "Song", "three.mp3", time="100.0"), 1), encoding="utf-8")
    out_path = tmp_path / "out.nml"

    result = run_tool(
        ["rewrite-from-collection-compare", str(old_path), str(new_path), str(out_path)], cwd=tmp_path
    )
    assert result.exit_code == 0
    assert "destination_collisions=2" in result.stdout


def test_sync_current_copy_is_preferred_over_sync_old_duplicate() -> None:
    def record(dir_value: str) -> EntryRecord:
        location = LocationParts("FreqKing", "FreqKing", dir_value, "song.mp3")
        return EntryRecord(
            entry=ET.Element("ENTRY", ARTIST="Artist", TITLE="Song"),
            artist="Artist", title="Song", audio_id="same-audio-id",
            filesize="100", playtime_float="200.0", bitrate="320", album="Album",
            file_name="song.mp3", location=location,
        )

    old = record("/:Users/:FreqKing/:Sync/:FreqKing_V02/:")
    current = record("/:Sync_/:FreqKing_V02/:")
    archived = record("/:Sync_old/:FreqKing_V02/:")

    mapping, stats, _samples = match_records([old], [archived, current], MatchConfidence.STRICT)

    assert mapping[old.primary_key] is current
    assert stats["matched"] == 1
    assert stats["ambiguous"] == 0
