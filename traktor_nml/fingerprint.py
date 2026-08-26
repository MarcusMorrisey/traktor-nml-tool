"""Acoustic fingerprint key provider (chromaprint via pyacoustid), local-only.

A fingerprint computed only from scanned/new candidates has nothing to
compare against because the OLD collection's original media is exactly what
may be unreachable - that's why reconnection exists. Fingerprinting is
therefore old-side-gated: only attempted when the old track's recorded path
is still resolvable on disk at scan time; otherwise it is silently absent for
that track (counted in stats, not an error) and matching falls through to the
tag-based cascade (DL-006, DL-013).

Duration must agree within +/-1.0s before comparing; similarity above 0.95
counts as a match; 0.80-0.95 is logged as fingerprint_near_match for human
review only, never auto-accepted.

Bridging continuous similarity into the cascade's exact-match key/index
architecture: candidates whose fingerprints agree with each other within
duration tolerance and match threshold are grouped into one cluster and share
one key (see _cluster_candidates), so that when an old record's best match
turns out to have company - e.g. two bitrate rips of the same track, both
clearing the threshold - the shared key's index bucket holds more than one
candidate and the ordinary ambiguity check reports it, rather than a single
first-found winner silently keeping the rest a secret.
"""

# HAS_ACOUSTID gates every entry point in this module, including ones
# that do not mention it by name below, so importing this module never
# requires the fpcalc binary to be installed.
#
# It is an IMPORT check, not a capability check. The tier needs three
# things - this module, the fpcalc binary to fingerprint with, and the
# chromaprint shared library to compare with - and HAS_ACOUSTID only sees
# the first. With fpcalc absent, _compute_fingerprint returns None and the
# tier is silently dark; with the shared library absent (the standalone
# fpcalc build does not ship it), fingerprinting works but every compare
# raises, which _similarity converts to "cannot compare" and counts in
# fingerprint_compare_errors. Both degrade to matching nothing rather than
# matching wrongly, but neither is visible in HAS_ACOUSTID.

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional

from .matching import AMBIGUOUS, KeyProvider
from .model import EntryRecord
from .volumes import local_path_for_location
from .tagcache import TagCache

# Availability is probed once here, at import time, rather than per call:
# HAS_ACOUSTID is the flag both the startup warning line and the
# active-provider stats counter (named per DL-006) read to report
# whether this tier is live.

try:
    import acoustid

    HAS_ACOUSTID = True
except (ImportError, OSError):  # pragma: no cover - fpcalc binary or module absent
    HAS_ACOUSTID = False

def fingerprint_unavailable_reason() -> Optional[str]:
    """Why the tier cannot match, or None when it genuinely can.

    HAS_ACOUSTID answers "did the import succeed", which is not the same
    question: the tier needs the module, the fpcalc binary to fingerprint
    with, and the chromaprint shared library to compare with, and a machine
    can have any subset. Each missing piece degrades to matching nothing, so
    without this probe --fingerprint looks like it ran and simply found no
    candidates.

    Probed on demand rather than at import: the compare call is cheap but
    every CLI invocation would pay for it, including the ones that never
    fingerprint anything.
    """
    if not HAS_ACOUSTID:
        return "pyacoustid is not installed"
    if shutil.which("fpcalc") is None:
        return "the fpcalc binary is not on PATH"
    try:
        # Two trivially valid fingerprints: this exercises the C bindings,
        # not the comparison's result, which is discarded.
        acoustid.compare_fingerprints((0, "AQAAAA"), (0, "AQAAAA"))
    except Exception:
        return (
            "the chromaprint shared library is not available "
            "(the standalone fpcalc build does not ship it)"
        )
    return None


DURATION_TOLERANCE_SECONDS = 1.0
MATCH_THRESHOLD = 0.95
NEAR_MATCH_THRESHOLD = 0.80

TIER_NAME = "fingerprint"


# fpcalc invocation, replicating pyacoustid's own fpcalc backend exactly:
# `fpcalc -length 120 <abspath>`, stdout piped, stderr discarded, output parsed
# as DURATION=<float> and FINGERPRINT=<ascii> lines. The FPCALC environment
# variable overrides the binary, as pyacoustid allows.
#
# Why own the child instead of calling acoustid.fingerprint_file: that helper
# exposes neither a timeout nor a handle on the process it spawns, so a
# cooperative cancel token checked between files cannot interrupt a call
# already blocked inside it, and one pathological file can stall a 20-minute
# scan indefinitely. Section 2 of the GUI plan names this as the only core
# change in phase 1 that is not purely additive.
#
# One behavioural difference is deliberate and worth stating: pyacoustid
# prefers an audioread + chromaprint-library path when both are present and
# only falls back to fpcalc otherwise, so on such a machine this now always
# uses fpcalc. Same algorithm, different decoder. _similarity continues to
# call pyacoustid's compare_fingerprints unchanged.
FPCALC_MAX_AUDIO_LENGTH = 120  # seconds; pyacoustid's MAX_AUDIO_LENGTH
FPCALC_TIMEOUT_SECONDS = 30.0
FPCALC_TERMINATE_GRACE_SECONDS = 5.0


def _parse_fpcalc_output(output: bytes) -> Optional[tuple[float, str]]:
    """DURATION and FINGERPRINT out of fpcalc's stdout, or None if either is
    missing or malformed. Absence is not an error here: the caller counts it
    and moves on, because one unreadable file must not stop a scan."""
    duration: Optional[float] = None
    fingerprint: Optional[str] = None
    for line in output.splitlines():
        key, separator, value = line.partition(b"=")
        if not separator:
            continue
        if key == b"DURATION":
            try:
                duration = float(value)
            except ValueError:
                return None
        elif key == b"FINGERPRINT":
            fingerprint = value.decode("ascii", errors="replace")
    if duration is None or fingerprint is None:
        return None
    return duration, fingerprint


class FpcalcSession:
    """Owns the fpcalc child process for one scan.

    At most one child is live at a time and it is published to a slot the
    canceller can reach, so cancelling a scan can terminate a fingerprint
    already in progress rather than waiting for it. Section 3.5 states the
    bound in wall-clock terms precisely because a blocked child emits no
    callbacks: a bound counted in callbacks could never trip.

    Terminating is idempotent, and once terminated the session refuses to
    spawn anything further - otherwise a cancel racing the next file would
    start a child nobody is left to reap.
    """

    def __init__(
        self,
        timeout: float = FPCALC_TIMEOUT_SECONDS,
        grace: float = FPCALC_TERMINATE_GRACE_SECONDS,
    ) -> None:
        self.timeout = timeout
        self.grace = grace
        self._lock = threading.Lock()
        self._child: Optional[subprocess.Popen] = None
        self._closed = False

    @property
    def child_pid(self) -> Optional[int]:
        """PID of the live child, or None. For tests asserting no survivor."""
        with self._lock:
            return self._child.pid if self._child is not None else None

    def fingerprint(self, path: Path, stats: dict[str, int]) -> Optional[tuple[float, str]]:
        stats.setdefault("fingerprint_timeout", 0)
        stats.setdefault("fingerprint_errors", 0)

        binary = os.environ.get("FPCALC", "fpcalc")
        command = [
            binary,
            "-length",
            str(FPCALC_MAX_AUDIO_LENGTH),
            os.path.abspath(os.path.expanduser(str(path))),
        ]

        with self._lock:
            if self._closed:
                return None
            try:
                child = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
                )
            except OSError:
                stats["fingerprint_errors"] += 1
                return None
            self._child = child

        try:
            output, _ = child.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            # A single pathological file must not stall the run: kill it,
            # count it, and let the scan continue to the next one.
            self._end(child)
            stats["fingerprint_timeout"] += 1
            return None
        finally:
            # In a finally so an exception on this path cannot orphan a child.
            with self._lock:
                if self._child is child:
                    self._child = None

        if child.returncode:
            # Includes the cancel case: terminate() makes communicate() return
            # with a non-zero status, which is not a fingerprint.
            stats["fingerprint_errors"] += 1
            return None
        return _parse_fpcalc_output(output)

    def terminate(self) -> None:
        """Stop the live child, if any, and refuse to start more.

        terminate() on Windows is TerminateProcess, which needs no
        cooperation from fpcalc - it has no signal handling to rely on.
        """
        with self._lock:
            self._closed = True
            child = self._child
        if child is not None:
            self._end(child)

    def _end(self, child: subprocess.Popen) -> None:
        """terminate, wait out the grace period, then kill."""
        try:
            child.terminate()
        except OSError:  # pragma: no cover - already gone
            pass
        try:
            child.wait(timeout=self.grace)
            return
        except subprocess.TimeoutExpired:
            pass
        try:
            child.kill()
            child.wait(timeout=self.grace)
        except (OSError, subprocess.TimeoutExpired):  # pragma: no cover - unkillable
            pass


def _compute_fingerprint(
    path: Path,
    session: Optional[FpcalcSession] = None,
    stats: Optional[dict[str, int]] = None,
) -> Optional[tuple[float, str]]:
    """Fingerprint one file through an owned fpcalc child.

    A session is created per call when none is supplied, which keeps every
    existing caller working; a scan that wants to cancel mid-fingerprint
    passes its own so there is a child to reach.
    """
    owned = session if session is not None else FpcalcSession()
    return owned.fingerprint(path, stats if stats is not None else {})


def _similarity(a: str, b: str, stats: dict[str, int]) -> Optional[float]:
    # acoustid.compare_fingerprints only reads the fingerprint half of each
    # (duration, fp) pair, so (0, a)/(0, b) is a valid call - but a decode or
    # compare failure here is a distinct outcome from a genuine similarity of
    # 0.0, and every caller makes a matching decision from this return value
    # alone (the stats dict is never consulted before deciding), so the
    # failure must be signalled through the return itself: None on failure,
    # distinct from a real 0.0 comparison, so a compare error is never
    # mistaken for "definitely not the same track".
    stats.setdefault("fingerprint_compare_errors", 0)
    try:
        return acoustid.compare_fingerprints((0, a), (0, b))
    except Exception:
        stats["fingerprint_compare_errors"] += 1
        return None


def _cached_fingerprint(
    path: Path,
    cache: TagCache,
    session: Optional[FpcalcSession] = None,
    stats: Optional[dict[str, int]] = None,
) -> Optional[tuple[float, str]]:
    try:
        file_stat = path.stat()
    except OSError:
        return None
    existing = cache.get(path, file_stat.st_size, file_stat.st_mtime) or {}
    if existing.get("fingerprint"):
        return float(existing["duration"]), existing["fingerprint"]
    result = _compute_fingerprint(path, session, stats)
    if result is not None:
        cache.put(path, file_stat.st_size, file_stat.st_mtime, {**existing, "duration": result[0], "fingerprint": result[1]})
    return result


def old_side_fingerprint(
    record: EntryRecord,
    cache: TagCache,
    stats: dict[str, int],
    known_mounts: dict[tuple[str, str], list[Path]],
    session: Optional[FpcalcSession] = None,
) -> Optional[tuple[float, str]]:
    """Fingerprint a collection record only when its recorded location
    resolves, through volume reattachment, to a readable file at scan
    time; count the unresolvable case so its absence is visible in the
    statistics rather than silent. known_mounts maps (VOLUME, VOLUMEID) to
    the mount anchors this run has established explicitly (see
    volumes.local_path_for_location) - an unknown volume pair or an
    ambiguous anchor is deliberately counted as unavailable rather than
    guessed, the same explicitness rule that already governs the
    candidate side."""
    stats.setdefault("fingerprint_unavailable_old_side", 0)
    path = local_path_for_location(record.location, known_mounts)
    if path is None:
        stats["fingerprint_unavailable_old_side"] += 1
        return None
    result = _cached_fingerprint(path, cache, session, stats)
    if result is None:
        stats["fingerprint_unavailable_old_side"] += 1
    return result


def _cluster_candidates(
    candidate_fps: dict[int, tuple[float, str]], stats: dict[str, int]
) -> dict[int, str]:
    """Group candidates whose fingerprints agree with each other within
    duration tolerance and the match threshold, and return each candidate's
    cluster key. Two candidates that are acoustically indistinguishable from
    one another - e.g. two bitrate rips of the same track - end up sharing
    one key, so a query that matches either lands in an index bucket sized
    by the whole cluster rather than a single object identity."""
    parent: dict[int, int] = {cid: cid for cid in candidate_fps}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[max(root_a, root_b)] = min(root_a, root_b)

    ids = list(candidate_fps)
    for i, cid_a in enumerate(ids):
        duration_a, fp_a = candidate_fps[cid_a]
        for cid_b in ids[i + 1:]:
            duration_b, fp_b = candidate_fps[cid_b]
            if abs(duration_a - duration_b) > DURATION_TOLERANCE_SECONDS:
                continue
            similarity = _similarity(fp_a, fp_b, stats)
            # None means the compare itself failed (see _similarity) - treated
            # as "cannot compare", never as a real similarity score, so a
            # failed compare cannot silently union two unrelated candidates.
            if similarity is not None and similarity > MATCH_THRESHOLD:
                union(cid_a, cid_b)

    return {cid: str(find(cid)) for cid in candidate_fps}


def fingerprint_key_provider(
    cache: TagCache,
    candidates: list[EntryRecord],
    stats: dict[str, int],
    known_mounts: dict[tuple[str, str], list[Path]],
    session: Optional[FpcalcSession] = None,
) -> KeyProvider:
    """Supply a top-tier match key for an old record when a fingerprint
    exists for both it and at least one candidate, their durations agree
    within tolerance, and similarity clears the match threshold. The
    0.80-0.95 band is counted as fingerprint_near_match for review and never
    yields a key. Yields nothing at all when the fingerprinting binary is
    unavailable."""
    stats.setdefault("fingerprint_near_match", 0)
    stats.setdefault("fingerprint_ambiguous", 0)

    candidate_fps: dict[int, tuple[float, str]] = {}
    if HAS_ACOUSTID:
        for candidate in candidates:
            if candidate.source_path is None:
                continue
            fp = _cached_fingerprint(candidate.source_path, cache, session, stats)
            if fp is not None:
                candidate_fps[id(candidate)] = fp

    cluster_key = _cluster_candidates(candidate_fps, stats) if HAS_ACOUSTID else {}

    def provide(record: EntryRecord) -> Optional[tuple[str, ...]]:
        """Per-record key: routes a candidate-side record to its
        fingerprint cluster's shared key, and an old-side record to that
        winning cluster only when duration and similarity both clear this
        provider's thresholds (DL-013)."""
        if not HAS_ACOUSTID:
            return None

        if record.entry is None:
            # Candidate side: emit its cluster's key whenever it has a
            # usable fingerprint, so an old record's winning key resolves to
            # every candidate acoustically indistinguishable from the winner.
            return (cluster_key[id(record)],) if id(record) in cluster_key else None

        old_fp = old_side_fingerprint(record, cache, stats, known_mounts, session)
        if old_fp is None:
            return None
        old_duration, old_value = old_fp

        # Collect every candidate that clears the match threshold against the
        # old record, not just the first: acoustic similarity need not be
        # transitive, so two candidates (e.g. two different-bitrate rips of
        # one source) can each independently clear the threshold here while
        # their mutual similarity falls short of the cluster threshold.
        winners: list[EntryRecord] = []
        for candidate in candidates:
            candidate_fp = candidate_fps.get(id(candidate))
            if candidate_fp is None:
                continue
            candidate_duration, candidate_value = candidate_fp
            if abs(candidate_duration - old_duration) > DURATION_TOLERANCE_SECONDS:
                continue
            similarity = _similarity(old_value, candidate_value, stats)
            # None means the compare itself failed (see _similarity) -
            # treated as "cannot compare", never as a real similarity score.
            if similarity is None:
                continue
            if similarity > MATCH_THRESHOLD:
                winners.append(candidate)
            elif NEAR_MATCH_THRESHOLD <= similarity <= MATCH_THRESHOLD:
                stats["fingerprint_near_match"] += 1

        if not winners:
            return None
        winner_keys = {cluster_key[id(winner)] for winner in winners}
        if len(winner_keys) > 1:
            # More than one distinct cluster key qualifies: the record is
            # genuinely ambiguous between them. Returning AMBIGUOUS (rather
            # than None) makes match_records place this record in the
            # ambiguous bucket outright, so a lower tag-based tier in the
            # same cascade can never silently resolve it to a single
            # confident match - a plain None here would be indistinguishable
            # from "this tier has nothing to say", letting a less specific
            # tier decide instead of the tier that actually found the
            # conflict. The counter is still kept for the aggregate view.
            stats["fingerprint_ambiguous"] += 1
            return AMBIGUOUS
        return (next(iter(winner_keys)),)

    return KeyProvider(tier_name=TIER_NAME, provide=provide)
