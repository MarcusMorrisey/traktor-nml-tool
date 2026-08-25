"""Fuzzy discovery stays review-only and works when disk files lack tags."""

from __future__ import annotations

import csv
from pathlib import Path

from tests.conftest import run_tool
from traktor_nml.discovery import rank_candidates, rank_collection_candidates
from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.tracklist import ParsedLine


def _candidate(path: Path, artist: str = "", title: str = "") -> EntryRecord:
    return EntryRecord(
        entry=None,
        artist=artist,
        title=title,
        audio_id="",
        filesize="1",
        playtime_float="",
        bitrate="",
        album="",
        file_name=path.name,
        location=LocationParts(volume="", volumeid="", dir_value="/:Music/:", file_name=path.name),
        source_path=path,
    )


def test_filename_discovery_normalizes_punctuation_and_traktor_prefix(tmp_path: Path) -> None:
    line = ParsedLine(1, "Sade - Smooth Operator (SPLATINUM Remix)", "Sade", "Smooth Operator (SPLATINUM Remix)")
    candidate = _candidate(tmp_path / "7A_110_Smooth Operator (SPLATINUM Remix)_Sade.mp3")

    matches = rank_candidates([line], [candidate], max_candidates=1, min_score=0.50)

    assert len(matches) == 1
    assert matches[0].candidate_path == candidate.source_path
    assert matches[0].source == "filename"
    assert matches[0].score >= 0.50


def test_tagged_candidate_uses_tag_metadata(tmp_path: Path) -> None:
    line = ParsedLine(1, "Pink Floyd - Proper Education", "Pink Floyd", "Proper Education")
    candidate = _candidate(tmp_path / "opaque-file.m4a", "Pink Floyd", "Proper Education")

    matches = rank_candidates([line], [candidate], max_candidates=1, min_score=0.90)

    assert matches[0].source == "tags"
    assert matches[0].score == 1.0


def test_no_candidate_row_is_retained_for_review(tmp_path: Path) -> None:
    line = ParsedLine(1, "Artist - Song", "Artist", "Song")
    candidate = _candidate(tmp_path / "unrelated.mp3")

    matches = rank_candidates([line], [candidate], max_candidates=1, min_score=0.99)

    assert matches[0].candidate_path is None
    assert matches[0].source == "none"


def test_collection_discovery_normalizes_artist_order(tmp_path: Path) -> None:
    line = ParsedLine(1, "Eric Prydz, Pink Floyd - Proper Education", "Eric Prydz, Pink Floyd", "Proper Education")
    candidate = _candidate(tmp_path / "track.m4a", "Pink Floyd, Eric Prydz", "Proper Education")

    matches = rank_collection_candidates([line], [candidate], max_candidates=1, min_score=0.90)

    assert matches[0].candidate == candidate
    assert matches[0].score >= 0.90


def test_discover_tracks_command_writes_review_csv(tmp_path: Path) -> None:
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("Artist - Song\n", encoding="utf-8")
    music = tmp_path / "music"
    music.mkdir()
    (music / "Artist - Song.mp3").write_bytes(b"placeholder")
    report = tmp_path / "review.csv"
    cache = tmp_path / "cache.json"

    result = run_tool(
        [
            "discover-tracks",
            str(tracklist),
            str(report),
            "--scan-root",
            str(music),
            "--cache",
            str(cache),
            "--min-score",
            "0.90",
        ],
        cwd=tmp_path,
    )

    assert result.exit_code == 0
    with report.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["candidate_path"].endswith("Artist - Song.mp3")
    assert rows[0]["source"] == "filename"
