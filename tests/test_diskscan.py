"""Filesystem candidate index behavior: dedup, cache resume, STEM handling."""

from __future__ import annotations

import os
import time
from pathlib import Path

from traktor_nml.diskscan import index_scan_roots
from traktor_nml.tagcache import TagCache


def _make_files(root: Path, names: list[str]) -> None:
    """Create root and empty placeholder files of a fixed size, standing
    in for real audio files since these tests exercise path/size/mtime
    identity, not audio content."""
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        (root / name).write_bytes(b"\x00" * 32)


def test_second_scan_over_unchanged_roots_performs_no_tag_reads(tmp_path: Path) -> None:
    root = tmp_path / "music"
    _make_files(root, ["a.mp3", "b.flac"])
    cache = TagCache(tmp_path / "cache.json")

    stats1: dict[str, int] = {}
    index_scan_roots([root], cache, stats=stats1)
    assert stats1["cache_misses"] == 2

    cache2 = TagCache(tmp_path / "cache.json")
    stats2: dict[str, int] = {}
    index_scan_roots([root], cache2, stats=stats2)
    assert stats2["cache_misses"] == 0
    assert stats2["cache_hits"] == 2


def test_touching_mtime_reads_exactly_that_file(tmp_path: Path) -> None:
    root = tmp_path / "music"
    _make_files(root, ["a.mp3", "b.flac"])
    cache = TagCache(tmp_path / "cache.json")
    index_scan_roots([root], cache)

    cache2 = TagCache(tmp_path / "cache.json")
    future = time.time() + 100
    os.utime(root / "a.mp3", (future, future))
    stats: dict[str, int] = {}
    index_scan_roots([root], cache2, stats=stats)
    assert stats["cache_misses"] == 1
    assert stats["cache_hits"] == 1


def test_overlapping_roots_yield_one_candidate_per_file(tmp_path: Path) -> None:
    root = tmp_path / "music"
    _make_files(root, ["a.mp3"])
    cache = TagCache(tmp_path / "cache.json")
    stats: dict[str, int] = {}
    records = index_scan_roots([root, root], cache, stats=stats)
    assert len(records) == 1
    assert stats["duplicates_skipped"] == 1


def test_stem_files_are_indexed(tmp_path: Path) -> None:
    root = tmp_path / "music"
    _make_files(root, ["track.stem.mp3"])
    cache = TagCache(tmp_path / "cache.json")
    records = index_scan_roots([root], cache)
    assert len(records) == 1
    assert records[0].file_name == "track.stem.mp3"
    assert records[0].entry is None
    assert records[0].audio_id == ""


def test_resumed_scan_matches_uninterrupted_scan(tmp_path: Path) -> None:
    root = tmp_path / "music"
    names = [f"track{i}.mp3" for i in range(5)]
    _make_files(root, names)

    cache_full = TagCache(tmp_path / "full.json")
    full_records = index_scan_roots([root], cache_full)

    # Simulate an interruption partway through a scan: a first pass reaches
    # only two of the five files - as if the process were killed right
    # after they were cached - and its entries persist to disk (flush_every
    # is set low so that partial progress is not lost). A fresh TagCache
    # instance then resumes over the full root: the two already-cached
    # files must come back as cache hits (not be re-read), the remaining
    # three as cache misses, and the combined result must still match an
    # uninterrupted full scan exactly.
    interrupted_cache = TagCache(tmp_path / "partial.json", flush_every=1)
    for name in names[:2]:
        path = root / name
        file_stat = path.stat()
        interrupted_cache.put(path.resolve(), file_stat.st_size, file_stat.st_mtime, {
            "artist": "", "title": "", "album": "", "playtime_float": "", "bitrate": "",
        })
    interrupted_cache.flush()

    resumed_cache = TagCache(tmp_path / "partial.json")
    resumed_stats: dict[str, int] = {}
    resumed_records = index_scan_roots([root], resumed_cache, stats=resumed_stats)

    assert resumed_stats["cache_hits"] == 2
    assert resumed_stats["cache_misses"] == 3
    assert {r.file_name for r in full_records} == {r.file_name for r in resumed_records}


def test_cache_flush_retries_a_transient_windows_file_lock(tmp_path: Path, monkeypatch) -> None:
    import traktor_nml.tagcache as tagcache

    cache = TagCache(tmp_path / "cache.json")
    path = tmp_path / "track.mp3"
    path.write_bytes(b"x")
    file_stat = path.stat()
    cache.put(path, file_stat.st_size, file_stat.st_mtime, None)

    original_replace = tagcache.os.replace
    calls = 0

    def replace_once_locked(source, destination):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("temporary lock")
        return original_replace(source, destination)

    monkeypatch.setattr(tagcache.os, "replace", replace_once_locked)
    cache.flush()

    assert calls == 2
    assert (tmp_path / "cache.json").exists()


def test_index_files_keeps_order_and_duplicates(tmp_path):
    """index_files returns one record per path in the order given, a
    repeated path twice, sizes in KB, source_path set, and a file with no
    readable tags as a record with empty tag fields.

    Mutation: index_files skips a resolved path it has already indexed,
        the way _enumerate_candidates deduplicates, so [b, a, b] yields
        two records.
    Observed:
        E   AssertionError: assert ['b.mp3', 'a.mp3'] == ['b.mp3', 'a.mp3', 'b.mp3']
        E     Right contains one more item: 'b.mp3'
    """
    from traktor_nml.diskscan import index_files

    a = tmp_path / "a.mp3"
    b = tmp_path / "b.mp3"
    a.write_bytes(b"\0" * 4096)
    b.write_bytes(b"\0" * 2048)
    records = index_files([b, a, b])
    assert [r.file_name for r in records] == ["b.mp3", "a.mp3", "b.mp3"]
    assert [r.filesize for r in records] == ["2", "4", "2"]
    assert all(r.source_path is not None and r.entry is None for r in records)
    assert (records[0].artist, records[0].title, records[0].playtime_float) == ("", "", "")


def test_index_files_raises_on_stat_failure(tmp_path):
    """A path that cannot be stat()ed mid-list raises DiskReadError
    naming it; no shorter list comes back.

    Mutation: index_files catches OSError from stat() with `continue` in
        place of raising DiskReadError, so no exception is raised.
    Observed:
        E   Failed: DID NOT RAISE <class 'traktor_nml.diskscan.DiskReadError'>
    """
    import pytest

    from traktor_nml.diskscan import DiskReadError, index_files

    present = tmp_path / "a.mp3"
    present.write_bytes(b"\0")
    missing = tmp_path / "gone.mp3"
    with pytest.raises(DiskReadError) as error:
        index_files([present, missing, present])
    assert error.value.path == missing.resolve()


def test_index_files_writes_no_cache_file_without_a_cache(tmp_path):
    """With cache None no file other than the inputs appears.

    Mutation: index_files, given cache None, creates
        TagCache(resolved.parent / 'tag_cache.json') and flushes it, so
        a tag_cache.json file appears beside a.mp3.
    Observed:
        E   AssertionError: assert ['a.mp3', 'tag_cache.json'] == ['a.mp3']
        E     Left contains one more item: 'tag_cache.json'
    """
    from traktor_nml.diskscan import index_files

    track = tmp_path / "a.mp3"
    track.write_bytes(b"\0")
    index_files([track])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.mp3"]
