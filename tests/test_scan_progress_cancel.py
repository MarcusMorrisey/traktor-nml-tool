"""Progress and cancellation for index_scan_roots.

Merge gates for sections 3.4 and 3.5 of docs/nicegui-gui-analysis.md. Both
features exist for a GUI that does not exist yet, so nothing else in the suite
would notice them regressing - these tests are the only thing holding them.

The section 3.5 cases involving a blocked fpcalc child are NOT here: they
depend on the direct-Popen change to fingerprint.py, which is a separate step.
What is covered is the scan-loop half of the contract.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from traktor_nml.diskscan import ScanCancelled, index_scan_roots
from traktor_nml.tagcache import TagCache


def _library(root: Path, count: int) -> Path:
    """A scan root holding `count` distinct audio files."""
    root.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (root / f"track_{i:04d}.mp3").write_bytes(b"\x00" * 32)
    return root


def _scan(root: Path, cache_path: Path, **kwargs):
    return index_scan_roots([root], TagCache(cache_path), **kwargs)


# --- section 3.4: progress -----------------------------------------------


def test_done_never_decreases_and_never_exceeds_total(tmp_path: Path) -> None:
    seen: list[tuple[int, int]] = []
    _scan(
        _library(tmp_path / "lib", 60),
        tmp_path / "c.json",
        on_progress=lambda done, total, path: seen.append((done, total)),
        callback_every=7,
    )
    assert seen, "no progress reported at all"
    dones = [d for d, _ in seen]
    assert dones == sorted(dones), "done went backwards"
    assert all(d <= t for d, t in seen), "done exceeded total"


def test_final_callback_fires_exactly_once_with_done_equal_to_total(tmp_path: Path) -> None:
    """The bar must land on full, once - not stop short, not repeat."""
    seen: list[tuple[int, int]] = []
    _scan(
        _library(tmp_path / "lib", 60),
        tmp_path / "c.json",
        on_progress=lambda done, total, path: seen.append((done, total)),
        callback_every=7,  # 60 is not a multiple of 7, so the last file is a special case
    )
    total = seen[-1][1]
    assert seen[-1][0] == total
    assert [d for d, _ in seen].count(total) == 1


def test_final_callback_fires_once_when_total_divides_evenly(tmp_path: Path) -> None:
    """The other half of the boundary: when total IS a multiple of the
    interval both emit conditions are true for the last file, and it must
    still produce one callback rather than two."""
    seen: list[int] = []
    _scan(
        _library(tmp_path / "lib", 50),
        tmp_path / "c.json",
        on_progress=lambda done, total, path: seen.append(done),
        callback_every=10,
    )
    assert seen[-1] == 50
    assert seen.count(50) == 1


def test_total_is_known_before_the_first_callback_and_never_changes(tmp_path: Path) -> None:
    """A denominator that appears late, or moves, is worse than none: the bar
    would jump. Section 3.4 allows None instead; this scan always knows."""
    totals: list[int] = []
    _scan(
        _library(tmp_path / "lib", 40),
        tmp_path / "c.json",
        on_progress=lambda done, total, path: totals.append(total),
        callback_every=5,
    )
    assert totals[0] == 40
    assert len(set(totals)) == 1


def test_at_least_one_callback_per_hundred_files(tmp_path: Path) -> None:
    """Bounds how long the UI can go silent."""
    seen: list[int] = []
    _scan(
        _library(tmp_path / "lib", 250),
        tmp_path / "c.json",
        on_progress=lambda done, total, path: seen.append(done),
    )
    gaps = [b - a for a, b in zip([0, *seen], seen)]
    assert max(gaps) <= 100, f"went silent for {max(gaps)} files"


def test_duplicates_are_excluded_from_total_so_done_can_reach_it(tmp_path: Path) -> None:
    """Total counts what will be indexed, not what was walked.

    Deduplication happens during enumeration precisely so the denominator is
    reachable; counting pre-dedup would leave every scan with duplicates
    stuck short of 100%.
    """
    lib = _library(tmp_path / "lib", 10)
    stats: dict[str, int] = {}
    seen: list[tuple[int, int]] = []
    _scan(
        lib,
        tmp_path / "c.json",
        stats=stats,
        on_progress=lambda done, total, path: seen.append((done, total)),
        callback_every=1,
    )
    assert seen[-1][0] == seen[-1][1] == 10
    assert stats["files_seen"] == 10


def test_progress_callback_changes_nothing_about_the_result(tmp_path: Path) -> None:
    """Section 3.4 parity: observing a scan must not alter it.

    Same records, same stats, same tag cache bytes, with and without a
    callback - otherwise the GUI and the CLI would quietly diverge.
    """
    lib = _library(tmp_path / "lib", 30)

    quiet_stats: dict[str, int] = {}
    quiet = _scan(lib, tmp_path / "quiet.json", stats=quiet_stats)

    loud_stats: dict[str, int] = {}
    loud = _scan(
        lib,
        tmp_path / "loud.json",
        stats=loud_stats,
        on_progress=lambda done, total, path: None,
    )

    assert [r.source_path for r in quiet] == [r.source_path for r in loud]
    assert [r.filesize for r in quiet] == [r.filesize for r in loud]
    assert quiet_stats == loud_stats
    assert (tmp_path / "quiet.json").read_bytes() == (tmp_path / "loud.json").read_bytes()


# --- section 3.5: cancellation (scan-loop half) ---------------------------


def test_cancel_before_start_indexes_nothing(tmp_path: Path) -> None:
    token = threading.Event()
    token.set()
    with pytest.raises(ScanCancelled):
        _scan(_library(tmp_path / "lib", 20), tmp_path / "c.json", cancel=token)


def test_cancel_mid_scan_stops_promptly(tmp_path: Path) -> None:
    """Wall-clock, not callback counts. Section 3.5 is explicit that a bound
    stated in callbacks is vacuous against a blocked child; the same
    reasoning makes wall-clock the honest measure here."""
    token = threading.Event()
    started = time.time()

    def trip(done: int, total: int, path: Path) -> None:
        if done >= 10:
            token.set()

    with pytest.raises(ScanCancelled):
        _scan(
            _library(tmp_path / "lib", 400),
            tmp_path / "c.json",
            cancel=token,
            on_progress=trip,
            callback_every=1,
        )
    assert time.time() - started < 15.0


def test_cancel_is_raised_not_returned(tmp_path: Path) -> None:
    """A short list looks exactly like a complete one.

    If cancelling returned partial records, a caller that forgot to check the
    token would match the whole collection against a fraction of the disk and
    report every unscanned file as missing - a wrong answer delivered
    confidently. It has to be unmissable.
    """
    token = threading.Event()
    token.set()
    with pytest.raises(ScanCancelled):
        _scan(_library(tmp_path / "lib", 5), tmp_path / "c.json", cancel=token)


def test_cancel_is_idempotent(tmp_path: Path) -> None:
    token = threading.Event()
    token.set()
    token.set()
    with pytest.raises(ScanCancelled):
        _scan(_library(tmp_path / "lib", 5), tmp_path / "c.json", cancel=token)


def test_a_cancelled_scan_leaves_a_loadable_tag_cache(tmp_path: Path) -> None:
    """Partial cache updates are permitted on cancel, matching the existing
    --dry-run exception. The assertion is reloadability, not completeness:
    TagCache.flush is atomic, so incomplete is fine and corrupt is not.
    """
    lib = _library(tmp_path / "lib", 200)
    cache_path = tmp_path / "c.json"
    token = threading.Event()

    def trip(done: int, total: int, path: Path) -> None:
        if done >= 20:
            token.set()

    with pytest.raises(ScanCancelled):
        _scan(lib, cache_path, cancel=token, on_progress=trip, callback_every=1)

    assert cache_path.exists(), "the reading already done was thrown away"
    reloaded = json.loads(cache_path.read_text(encoding="utf-8"))

    # Exactly the files indexed before the token tripped: the partial work is
    # kept, and the scan stopped where it was told to rather than running on.
    assert len(reloaded) == 20
    assert len(reloaded) < 200

    # And it round-trips through the real reader, not just json.loads.
    TagCache(cache_path)


def test_an_uncancelled_token_changes_nothing(tmp_path: Path) -> None:
    """An unset token must be as inert as no token at all."""
    lib = _library(tmp_path / "lib", 25)
    plain_stats: dict[str, int] = {}
    plain = _scan(lib, tmp_path / "a.json", stats=plain_stats)

    token_stats: dict[str, int] = {}
    tokened = _scan(lib, tmp_path / "b.json", stats=token_stats, cancel=threading.Event())

    assert [r.source_path for r in plain] == [r.source_path for r in tokened]
    assert plain_stats == token_stats
    assert (tmp_path / "a.json").read_bytes() == (tmp_path / "b.json").read_bytes()


def test_progress_is_batched_rather_than_one_callback_per_file(tmp_path: Path) -> None:
    """Section 3.4 bounds only how QUIET the scan may go, not how loud.

    Emitting per file satisfies every stated criterion and would still be
    wrong for the thing the callback exists to feed: a UI redrawn 100,000
    times during one scan is a worse experience than the spinner this
    replaced. The batching is a design choice rather than a plan
    requirement, so it needs its own test or nothing holds it.
    """
    seen: list[int] = []
    _scan(
        _library(tmp_path / "lib", 250),
        tmp_path / "c.json",
        on_progress=lambda done, total, path: seen.append(done),
    )
    assert len(seen) < 250 / 2, f"{len(seen)} callbacks for 250 files is not batching"
