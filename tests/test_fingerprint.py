"""Fingerprint key provider: local-only, threshold-gated, degrades cleanly."""

from __future__ import annotations

import array
import math
import shutil
import subprocess
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from traktor_nml.confidence import MatchConfidence
from traktor_nml.fingerprint import (
    HAS_ACOUSTID,
    fingerprint_key_provider,
    fingerprint_unavailable_reason,
    old_side_fingerprint,
)

if HAS_ACOUSTID:  # pragma: no cover - import guard mirrors the module under test
    import acoustid
from traktor_nml.matching import match_records
from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.reconnect import location_from_disk_path
from traktor_nml.volumes import local_path_for_location
from traktor_nml.tagcache import TagCache

requires_acoustid = pytest.mark.skipif(
    not HAS_ACOUSTID, reason="pyacoustid/fpcalc not installed in this environment"
)


def _fingerprinting_unavailable() -> str | None:
    """Why a test cannot fingerprint, or None when it can.

    Stops one step short of the production probe: a test that only computes
    fingerprints needs the module and the binary, not the shared library
    that comparing needs.
    """
    if not HAS_ACOUSTID:
        return "pyacoustid is not installed"
    if shutil.which("fpcalc") is None:
        return "the fpcalc binary is not on PATH"
    return None


# The reasons are computed, not written out, because the three dependencies
# fail independently and a fixed string is wrong for two cases out of three.
# A skip that misreports its own cause sends the reader after the wrong
# dependency - which is the same defect these tests exist to pin in the
# tool, so it would be a poor look to ship it in the tests themselves.
_FINGERPRINTING_UNAVAILABLE = _fingerprinting_unavailable()
_COMPARISON_UNAVAILABLE = fingerprint_unavailable_reason()

requires_fingerprinting = pytest.mark.skipif(
    _FINGERPRINTING_UNAVAILABLE is not None,
    reason=f"cannot fingerprint: {_FINGERPRINTING_UNAVAILABLE}",
)
requires_comparison = pytest.mark.skipif(
    _COMPARISON_UNAVAILABLE is not None,
    reason=f"cannot compare fingerprints: {_COMPARISON_UNAVAILABLE}",
)
requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg needed to encode the audio fixtures"
)


# --- deterministic audio fixtures ---------------------------------------
#
# Generated rather than committed: a checked-in pair of MP3s would be
# opaque binary in the repository, and the property under test is about
# two ENCODINGS of one source, which only means anything if the source is
# known. A chirp plus a slower second voice gives chromaprint real
# spectral structure to key on - near-silence or a single steady tone
# produces a degenerate fingerprint that would make the test meaningless.

# 22,050 Hz is plenty: chromaprint downsamples to 11,025 Hz internally, so a
# higher rate costs generation and encode time and buys nothing. Clips are the
# shortest that still fingerprint stably - the suite runs on every commit and
# this module was doubling its wall time at 44.1 kHz and 20-second clips.
_RATE = 22050
_CLIP_SECONDS = 8.0


def _write_wav(path: Path, seconds: float = _CLIP_SECONDS) -> Path:
    count = int(_RATE * seconds)
    frames = array.array("h", bytes(2 * count))
    two_pi = 2 * math.pi
    for n in range(count):
        t = n / _RATE
        rising = 200 + 3800 * (t / seconds)
        value = 0.45 * math.sin(two_pi * rising * t)
        value += 0.25 * math.sin(two_pi * (110 + 40 * math.sin(two_pi * 0.25 * t)) * t)
        value *= 0.6 + 0.4 * math.sin(two_pi * 0.5 * t)
        frames[n] = int(max(-1.0, min(1.0, value)) * 30000)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(_RATE)
        handle.writeframes(frames.tobytes())
    return path


def _encode(source: Path, destination: Path, bitrate: str) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-b:a", bitrate, str(destination)],
        check=True,
        capture_output=True,
    )
    return destination


def _entry_element(artist: str = "A", title: str = "One") -> ET.Element:
    """A real ENTRY element, not a bare sentinel.

    entry only has to be non-None for match_records to treat the record as
    old-side, so a plain object() looks sufficient - but the moment a record
    actually MATCHES, match_records builds a sample row through
    record_label(), which reads entry.attrib. Every test here predates the
    tier being able to match anything, so the sentinel survived; the first
    test to match on a fingerprint crashed on it.
    """
    return ET.Element("ENTRY", {"ARTIST": artist, "TITLE": title})


def _old_record(path: Path) -> EntryRecord:
    return EntryRecord(
        entry=_entry_element(),
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


@requires_ffmpeg
@requires_comparison
def test_two_bitrate_encodings_match_by_fingerprint(tmp_path: Path) -> None:
    """The tier's whole reason to exist: one recording, two encodings, no
    usable tags, different filenames - matched on the audio itself.

    Nothing else in the cascade can do this. The tag tiers need tags, and
    the path tiers need the file to have kept its place, so if the
    fingerprint tier silently stopped matching, every other test would
    still pass.
    """
    source = _write_wav(tmp_path / "source.wav")
    old_file = _encode(source, tmp_path / "old" / "rip_128.mp3", "128k")
    new_file = _encode(source, tmp_path / "new" / "different_name_320.mp3", "320k")

    cache = TagCache(tmp_path / "cache.json")
    stats: dict[str, int] = {}
    location = location_from_disk_path(old_file, "VOL", "VOLID")
    known_mounts = {("VOL", "VOLID"): [Path(old_file.anchor)]}

    candidates = [_candidate(new_file)]
    provider = fingerprint_key_provider(cache, candidates, stats, known_mounts)
    mapping, match_stats, _ = match_records(
        [_old_record_at(location)], candidates, MatchConfidence.STRICT, [provider]
    )

    assert match_stats["matched"] == 1
    assert match_stats["matched_fingerprint"] == 1
    assert stats["fingerprint_compare_errors"] == 0
    assert next(iter(mapping.values())).source_path == new_file


@requires_ffmpeg
@requires_fingerprinting
def test_pair_outside_duration_tolerance_never_compared(tmp_path: Path) -> None:
    """Duration is the cheap pre-filter in front of the expensive compare.

    Two files whose durations differ by more than the tolerance must never
    reach compare_fingerprints at all - the gate exists to avoid the cost,
    so asserting only "they did not match" would pass even if the gate were
    deleted and the comparison merely came back low. This spies on the
    comparison instead, which is the behaviour the gate actually promises.

    Needs no working chromaprint library precisely because nothing should
    call into it.
    """
    import traktor_nml.fingerprint as fingerprint_module

    short_file = _encode(_write_wav(tmp_path / "short.wav", seconds=3), tmp_path / "old" / "a.mp3", "128k")
    long_file = _encode(_write_wav(tmp_path / "long.wav", seconds=12), tmp_path / "new" / "b.mp3", "128k")

    calls: list[tuple[str, str]] = []

    def _spy(a: str, b: str, stats: dict[str, int]):
        calls.append((a, b))
        return 1.0  # a perfect score, so only the duration gate can prevent a match

    monkeypatched = pytest.MonkeyPatch()
    monkeypatched.setattr(fingerprint_module, "_similarity", _spy)
    try:
        cache = TagCache(tmp_path / "cache.json")
        stats: dict[str, int] = {}
        location = location_from_disk_path(short_file, "VOL", "VOLID")
        known_mounts = {("VOL", "VOLID"): [Path(short_file.anchor)]}

        candidates = [_candidate(long_file)]
        provider = fingerprint_key_provider(cache, candidates, stats, known_mounts)
        _, match_stats, _ = match_records(
            [_old_record_at(location)], candidates, MatchConfidence.STRICT, [provider]
        )
    finally:
        monkeypatched.undo()

    assert calls == [], "durations 8s apart must be rejected before any comparison"
    assert match_stats["matched_fingerprint"] == 0


@requires_ffmpeg
@requires_fingerprinting
def test_comparison_unavailable_degrades_to_no_match(tmp_path: Path) -> None:
    """A machine can have pyacoustid AND fpcalc and still be unable to
    compare: fingerprinting shells out to the binary, but comparing calls
    the chromaprint shared library, which the standalone fpcalc build does
    not ship. HAS_ACOUSTID reports True throughout.

    The tier must then match NOTHING rather than match wrongly, and must
    say so in the stats instead of looking like a clean run that found no
    candidates. Two encodings of one source are used, so a working
    comparison would certainly match them - the only reason there is no
    match here is the failure being handled.
    """
    import traktor_nml.fingerprint as fingerprint_module

    source = _write_wav(tmp_path / "source.wav")
    old_file = _encode(source, tmp_path / "old" / "rip_128.mp3", "128k")
    new_file = _encode(source, tmp_path / "new" / "rip_320.mp3", "320k")

    def _broken_compare(a, b):
        raise ModuleNotFoundError("function needs chromaprint")

    monkeypatched = pytest.MonkeyPatch()
    monkeypatched.setattr(fingerprint_module.acoustid, "compare_fingerprints", _broken_compare)
    try:
        cache = TagCache(tmp_path / "cache.json")
        stats: dict[str, int] = {}
        location = location_from_disk_path(old_file, "VOL", "VOLID")
        known_mounts = {("VOL", "VOLID"): [Path(old_file.anchor)]}

        candidates = [_candidate(new_file)]
        provider = fingerprint_key_provider(cache, candidates, stats, known_mounts)
        _, match_stats, _ = match_records(
            [_old_record_at(location)], candidates, MatchConfidence.STRICT, [provider]
        )
    finally:
        monkeypatched.undo()

    assert match_stats["matched_fingerprint"] == 0
    assert match_stats["unmatched"] == 1
    # The failure is recorded, not swallowed: without this counter an
    # unusable tier is indistinguishable from one that simply found nothing.
    assert stats["fingerprint_compare_errors"] > 0


def _old_record_at(location: LocationParts) -> EntryRecord:
    return EntryRecord(
        entry=_entry_element(),
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
