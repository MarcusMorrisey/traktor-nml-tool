"""Direct-core capture tests for the two scan diagnostics the parity
oracle cannot reach: no manifest case runs without mutagen, and no
fixture crosses the 500-file progress threshold. Each half of DL-056 -
default-print-to-stderr, and additive-collector-instead - is exercised for
both diagnostics, plus a leak-detector at run_reconnection level.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from traktor_nml import diskscan, reconnect_run
from traktor_nml.diskscan import _tag_free_summary, index_scan_roots
from traktor_nml.tagcache import TagCache


def _make_files(root: Path, count: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (root / f"track_{i:04d}.mp3").write_bytes(b"")


def test_missing_mutagen_prints_to_stderr_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """With no on_diagnostic, the exact tag_reading_unavailable line
    reaches stderr and nothing reaches stdout - reproducing today's
    default behaviour."""
    monkeypatch.setattr(diskscan, "HAS_MUTAGEN", False)
    root = tmp_path / "audio"
    _make_files(root, 1)
    cache = TagCache(tmp_path / "cache.json")

    index_scan_roots([root], cache)

    captured = capsys.readouterr()
    expected = (
        "tag_reading_unavailable=mutagen not installed; tiers still able to match, "
        "by --match-confidence level: " + _tag_free_summary()
    )
    assert captured.out == ""
    assert captured.err.strip() == expected


def test_missing_mutagen_with_collector_writes_no_stream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """With a collector supplied, capsys sees nothing on either stream
    and the collector holds the same line that would otherwise have
    printed - proving the transport is additive rather than replacing
    the default. Observed to fail when _emit_diagnostic's body is
    replaced with an unconditional print(line, file=sys.stderr),
    removing the `if on_diagnostic is not None` check: captured.err
    then holds the tag_reading_unavailable line instead of ""."""
    monkeypatch.setattr(diskscan, "HAS_MUTAGEN", False)
    root = tmp_path / "audio"
    _make_files(root, 1)
    cache = TagCache(tmp_path / "cache.json")
    collected: list[str] = []

    index_scan_roots([root], cache, on_diagnostic=collected.append)

    captured = capsys.readouterr()
    expected = (
        "tag_reading_unavailable=mutagen not installed; tiers still able to match, "
        "by --match-confidence level: " + _tag_free_summary()
    )
    assert captured.out == ""
    assert captured.err == ""
    assert collected == [expected]


def test_progress_lines_print_to_stderr_in_order_by_default(tmp_path: Path, capsys) -> None:
    """With no on_diagnostic, disk_scan_progress lines appear on stderr
    in ascending order as the walk crosses progress_every repeatedly."""
    root = tmp_path / "audio"
    _make_files(root, 11)
    cache = TagCache(tmp_path / "cache.json")

    index_scan_roots([root], cache, progress_every=3)

    captured = capsys.readouterr()
    assert captured.out == ""
    lines = [line for line in captured.err.splitlines() if line.startswith("disk_scan_progress=")]
    counts = [int(line.split("=", 1)[1]) for line in lines]
    assert counts == sorted(counts)
    assert counts == [3, 6, 9]


def test_progress_lines_with_collector_are_ordered_and_stream_is_empty(tmp_path: Path, capsys) -> None:
    """With a collector, the same ordered progress lines land in the
    collector instead, and stderr is empty. Observed to fail when
    _emit_diagnostic's body is replaced with an unconditional
    print(line, file=sys.stderr), removing the `if on_diagnostic is
    not None` check: captured.err then holds all three progress lines,
    "disk_scan_progress=3\ndisk_scan_progress=6\ndisk_scan_progress=9\n",
    instead of ""."""
    root = tmp_path / "audio"
    _make_files(root, 11)
    cache = TagCache(tmp_path / "cache.json")
    collected: list[str] = []

    index_scan_roots([root], cache, progress_every=3, on_diagnostic=collected.append)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    counts = [int(line.split("=", 1)[1]) for line in collected if line.startswith("disk_scan_progress=")]
    assert counts == [3, 6, 9]


def test_tag_reading_unavailable_precedes_every_progress_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both conditions together: tag_reading_unavailable is always first,
    ahead of every disk_scan_progress line, because the mutagen check is
    the first statement in index_scan_roots and the progress check lives
    inside the walk. Observed to fail when _emit_diagnostic's body is
    replaced with an unconditional print(line, file=sys.stderr),
    removing the `if on_diagnostic is not None` check: on_diagnostic is
    then never called, so collected stays empty and collected[0] raises
    IndexError."""
    monkeypatch.setattr(diskscan, "HAS_MUTAGEN", False)
    root = tmp_path / "audio"
    _make_files(root, 11)
    cache = TagCache(tmp_path / "cache.json")
    collected: list[str] = []

    index_scan_roots([root], cache, progress_every=3, on_diagnostic=collected.append)

    assert collected[0].startswith("tag_reading_unavailable=")
    progress_indices = [i for i, line in enumerate(collected) if line.startswith("disk_scan_progress=")]
    assert progress_indices and all(i > 0 for i in progress_indices)


def _reconnect_args(scan_root: Path, cache_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        scan_roots=[scan_root],
        refresh_cache=False,
        cache=cache_path,
        volume_map=[[str(scan_root), "D:", "D:"]],
        match_confidence="filename",
        allow_artist_title_only=False,
        no_refute=False,
        fingerprint=False,
    )


def test_run_reconnection_writes_no_stream_without_mutagen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """Leak detector at core level: run_reconnection with mutagen absent
    writes nothing to either stream, because its scan diagnostics are
    collected via on_diagnostic rather than printed. This is the test
    that fails first if a future change reintroduces a print into the
    pipeline. Observed to fail when _emit_diagnostic's body is replaced
    with an unconditional print(line, file=sys.stderr), removing the
    `if on_diagnostic is not None` check: captured.err then holds the
    tag_reading_unavailable line instead of ""."""
    monkeypatch.setattr(diskscan, "HAS_MUTAGEN", False)
    root = tmp_path / "audio"
    _make_files(root, 1)
    args = _reconnect_args(root, tmp_path / "cache.json")
    old_root = _empty_collection_root()

    result = reconnect_run.run_reconnection(args, old_root)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert any(line.startswith("tag_reading_unavailable=") for line in result.diagnostics)


def test_run_reconnection_writes_no_stream_across_progress_threshold(tmp_path: Path, capsys) -> None:
    """Leak detector at core level, second condition: a scan large enough
    to cross the default 500-file progress threshold still writes
    nothing to either stream from inside run_reconnection. Observed to
    fail when _emit_diagnostic's body is replaced with an unconditional
    print(line, file=sys.stderr), removing the `if on_diagnostic is not
    None` check: captured.err then holds "disk_scan_progress=500\n"
    instead of ""."""
    root = tmp_path / "audio"
    _make_files(root, 501)
    args = _reconnect_args(root, tmp_path / "cache.json")
    old_root = _empty_collection_root()

    result = reconnect_run.run_reconnection(args, old_root)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert any(line.startswith("disk_scan_progress=") for line in result.diagnostics)


def _empty_collection_root():
    """A minimal COLLECTION root with no entries, sufficient for
    collection_records() to return an empty list."""
    from traktor_nml.xmlio import ET

    root = ET.Element("NML")
    collection = ET.SubElement(root, "COLLECTION")
    collection.set("ENTRIES_COUNT", "0")
    return root
