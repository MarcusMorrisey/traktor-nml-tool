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

# HAS_ACOUSTID gates every entry point in this module, including ones
# that do not mention it by name below, so importing this module never
# requires the fpcalc binary to be installed.

Bridging continuous similarity into the cascade's exact-match key/index
architecture: candidates whose fingerprints agree with each other within
duration tolerance and match threshold are grouped into one cluster and share
one key (see _cluster_candidates), so that when an old record's best match
turns out to have company - e.g. two bitrate rips of the same track, both
clearing the threshold - the shared key's index bucket holds more than one
candidate and the ordinary ambiguity check reports it, rather than a single
first-found winner silently keeping the rest a secret.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .matching import AMBIGUOUS, KeyProvider
from .model import EntryRecord
from .tagcache import TagCache

try:
    import acoustid

    HAS_ACOUSTID = True
except (ImportError, OSError):  # pragma: no cover - fpcalc binary or module absent
    HAS_ACOUSTID = False

DURATION_TOLERANCE_SECONDS = 1.0
MATCH_THRESHOLD = 0.95
NEAR_MATCH_THRESHOLD = 0.80

TIER_NAME = "fingerprint"


def _compute_fingerprint(path: Path) -> Optional[tuple[float, str]]:
    if not HAS_ACOUSTID:
        return None
    try:
        duration, fp = acoustid.fingerprint_file(str(path))
    except Exception:
        return None
    return float(duration), fp if isinstance(fp, str) else fp.decode("ascii")


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


def _cached_fingerprint(path: Path, cache: TagCache) -> Optional[tuple[float, str]]:
    try:
        file_stat = path.stat()
    except OSError:
        return None
    existing = cache.get(path, file_stat.st_size, file_stat.st_mtime) or {}
    if existing.get("fingerprint"):
        return float(existing["duration"]), existing["fingerprint"]
    result = _compute_fingerprint(path)
    if result is not None:
        cache.put(path, file_stat.st_size, file_stat.st_mtime, {**existing, "duration": result[0], "fingerprint": result[1]})
    return result


def old_side_fingerprint(
    record: EntryRecord, cache: TagCache, stats: dict[str, int]
) -> Optional[tuple[float, str]]:
    """Fingerprint a collection record only when its recorded location
    resolves to a readable file at scan time; count the unresolvable case
    so its absence is visible in the statistics rather than silent."""
    stats.setdefault("fingerprint_unavailable_old_side", 0)
    path = Path(str(record.location.decoded_path))
    if not path.is_file():
        stats["fingerprint_unavailable_old_side"] += 1
        return None
    result = _cached_fingerprint(path, cache)
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
def fingerprint_key_provider(cache: TagCache, candidates: list[EntryRecord], stats: dict[str, int]) -> KeyProvider:
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
            fp = _cached_fingerprint(candidate.source_path, cache)
            if fp is not None:
        """Per-record key: routes a candidate-side record to its
        fingerprint cluster's shared key, and an old-side record to that
        winning cluster only when duration and similarity both clear this
        provider's thresholds (DL-013)."""
                candidate_fps[id(candidate)] = fp

    cluster_key = _cluster_candidates(candidate_fps, stats) if HAS_ACOUSTID else {}

    def provide(record: EntryRecord) -> Optional[tuple[str, ...]]:
        if not HAS_ACOUSTID:
            return None

        if record.entry is None:
            # Candidate side: emit its cluster's key whenever it has a
            # usable fingerprint, so an old record's winning key resolves to
            # every candidate acoustically indistinguishable from the winner.
            return (cluster_key[id(record)],) if id(record) in cluster_key else None

        old_fp = old_side_fingerprint(record, cache, stats)
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
            if similarity is not None and similarity > MATCH_THRESHOLD:
                union(cid_a, cid_b)

    return {cid: str(find(cid)) for cid in candidate_fps}


