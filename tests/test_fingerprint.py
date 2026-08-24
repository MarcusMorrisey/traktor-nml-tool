"""Fingerprint key provider: local-only, threshold-gated, degrades cleanly."""

from __future__ import annotations

from pathlib import Path

import pytest

from traktor_nml.confidence import MatchConfidence
from traktor_nml.fingerprint import HAS_ACOUSTID, fingerprint_key_provider, old_side_fingerprint
from traktor_nml.matching import match_records
from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.reconnect import location_from_disk_path
from traktor_nml.volumes import local_path_for_location
from traktor_nml.tagcache import TagCache

requires_acoustid = pytest.mark.skipif(
    not HAS_ACOUSTID, reason="pyacoustid/fpcalc not installed in this environment"
)


def _old_record(path: Path) -> EntryRecord:
    return EntryRecord(
        entry=object(),  # any non-None sentinel marks this as an old-side record
        artist="", title="", audio_id="", filesize="", playtime_float="", bitrate="", album="",
        file_name=path.name,
        location=LocationParts(volume="", volumeid="", dir_value=f"/:{path.parent.name}/:", file_name=path.name),
    )


def _candidate(path: Path) -> EntryRecord:
    """Disk-derived EntryRecord stub: entry=None marks the candidate side
    the same way diskscan.index_scan_roots does, so match_records treats
    it identically to a real scanned file."""
    return EntryRecord(
        entry=None, artist="", title="", audio_id="", filesize="", playtime_float="", bitrate="", album="",
        file_name=path.name,
        location=LocationParts(volume="", volumeid="", dir_value="/:", file_name=path.name),
        source_path=path,
    )


def test_provider_yields_nothing_when_binary_unavailable(tmp_path: Path) -> None:
    """Matching results are identical with the provider absent and with it
    present but unavailable, since an unavailable binary makes provide()
    return None unconditionally."""
    cache = TagCache(tmp_path / "cache.json")
    old = _old_record(tmp_path / "gone" / "song.mp3")
    candidates = [_candidate(tmp_path / "song.mp3")]
    stats: dict[str, int] = {}
    provider = fingerprint_key_provider(cache, candidates, stats, {})

    without_provider = match_records([old], candidates, MatchConfidence.STRICT, [])
    with_unavailable_provider = match_records([old], candidates, MatchConfidence.STRICT, [provider])

    assert without_provider[1]["matched"] == with_unavailable_provider[1]["matched"]


@requires_acoustid
def test_two_bitrate_encodings_match_by_fingerprint(tmp_path: Path) -> None:
    pytest.skip("requires real audio fixtures encoded at two bitrates; exercised in the manual rollout gate")


@requires_acoustid
def test_pair_outside_duration_tolerance_never_compared(tmp_path: Path) -> None:
    pytest.skip("requires real audio fixtures; exercised in the manual rollout gate")


def _old_record_at(location: LocationParts) -> EntryRecord:
    return EntryRecord(
        entry=object(),
        artist="", title="", audio_id="", filesize="", playtime_float="", bitrate="", album="",
        file_name=location.file_name,
        location=location,
    )


def test_old_side_location_resolves_to_the_file_it_was_encoded_from(
    tmp_path: Path, monkeypatch
) -> None:
    """Round-tripping a real file through location_from_disk_path and back
    through local_path_for_location, with that file's own volume identity
    registered as a known mount, must reproduce the exact same path - this
    holds without pyacoustid installed, unlike a real fingerprint
    comparison, so it is the assertion this test relies on.

    known_mounts is keyed by the file's VOLUME ROOT (the drive letter or
    POSIX root that location_from_disk_path itself strips as the path's
    anchor), never by an arbitrary subdirectory such as the file's parent
    - decoded_path is relative to the volume root, not to any particular
    scan-root subdirectory, so only the volume-root anchor reconstructs
    the original absolute path.

    old_side_fingerprint's fingerprint_unavailable_old_side counter also
    absorbs a failed fingerprint computation (e.g. pyacoustid/fpcalc not
    installed in this environment), not only a path-resolution failure, so
    the path-resolution step is isolated here by stubbing
    _cached_fingerprint to succeed whenever the resolved path is the real
    file - independent of whether real fingerprinting is available.
    """
    import traktor_nml.fingerprint as fingerprint_module

    def _stub_cached_fingerprint(path, cache):
        return (1.0, "stub-fingerprint") if path == real_dir / "song.mp3" else None

    monkeypatch.setattr(fingerprint_module, "_cached_fingerprint", _stub_cached_fingerprint)

    real_dir = tmp_path / "anchor"
    real_dir.mkdir()
    real_file = real_dir / "song.mp3"
    real_file.write_bytes(b"data")

    location = location_from_disk_path(real_file, "VOL", "VOLID")
    anchor = Path(real_file.anchor)
    known_mounts = {("VOL", "VOLID"): [anchor]}
    assert local_path_for_location(location, known_mounts) == real_file

    cache = TagCache(tmp_path / "cache.json")

    known_stats: dict[str, int] = {}
    old_side_fingerprint(_old_record_at(location), cache, known_stats, known_mounts)
    assert known_stats["fingerprint_unavailable_old_side"] == 0

    unknown_location = location_from_disk_path(real_file, "OTHER", "OTHER")
    unknown_stats: dict[str, int] = {}
    old_side_fingerprint(_old_record_at(unknown_location), cache, unknown_stats, known_mounts)
    assert unknown_stats["fingerprint_unavailable_old_side"] == 1

    # A decoy file at the same volume-relative path under a second,
    # unmapped anchor must never be picked - mirror the relative directory
    # structure (everything below the volume-root anchor) under a
    # separate decoy root and place a different file there.
    relative_parts = location.decoded_dir.parts[1:]  # drop the leading "/"
    decoy_root = tmp_path / "decoy_root"
    (decoy_root.joinpath(*relative_parts)).mkdir(parents=True)
    (decoy_root.joinpath(*relative_parts, "song.mp3")).write_bytes(b"different data, not the same file")

    single_anchor_mounts = {("VOL", "VOLID"): [anchor]}
    assert local_path_for_location(location, single_anchor_mounts) == real_file

    two_anchor_mounts = {("VOL", "VOLID"): [anchor, decoy_root]}
    assert local_path_for_location(location, two_anchor_mounts) is None
