"""Tiered match-key cascade and pairwise old-vs-new matching.

record_keys and match_records are reused unmodified (module-level, not
subclassed or wrapped) by disk-scan reconnection: a filesystem candidate is
just an EntryRecord with entry=None fed in as the "new" side. Fingerprinting
plugs in as an injected key provider (see fingerprint.py) rather than a
parameter on this cascade directly, so this module stays free of any
chromaprint/network dependency and keeps behaving identically when no
providers are supplied.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from .confidence import MatchConfidence
from .model import EntryRecord, record_label

_BASE_STAT_TIERS: tuple[str, ...] = (
    # Fixed tier ordering used to initialise per-tier match-count stats
    # keys before matching runs, so a zero-count tier still prints
    # alongside tiers that matched; injected key providers (DL-006) add
    # their own tier names to the printed stats without editing this tuple.
    "audio_id",
    "artist_title_size_time",
    "artist_title_file",
    "file_size_time",
    "artist_title_album_time",
    "artist_title",
)

_EXTRA_STAT_TIERS: tuple[str, ...] = (
    # Tiers added after the stats dict was first pinned, in cascade order.
    # Unlike _BASE_STAT_TIERS these are printed only when the run's
    # confidence admits them (see match_records).
    "path_suffix_3",
    "path_suffix_2",
    "path_suffix_1",
    "filename",
)

AMBIGUOUS = object()
"""Sentinel a KeyProvider.provide() may return in place of a key tuple to
force this record into the ambiguous bucket, regardless of what any lower,
less specific tier in the same cascade would otherwise resolve confidently.
Distinct from None, which means the provider has nothing to contribute for
this record and the cascade proceeds to the next tier exactly as if the
provider were absent: a provider can positively detect its own unresolvable
multi-candidate conflict (e.g. acoustic fingerprint similarity, where
candidates need not cluster transitively, so several can independently
clear a match threshold against one old record without agreeing with each
other) in a way the ordinary key/index bucket-size check never sees, since
that conflict lives inside the provider's own comparison rather than in a
shared index bucket."""


@dataclass(frozen=True)
class KeyProvider:
    """An injected top-tier match key provider (see fingerprint.py).

    tier_name is fixed and known without calling provide, so match_records
    can size its stats dict without probing a record (which would risk
    triggering the provider's own side effects, e.g. hashing a file). provide
    returns None when it has nothing to contribute for this record - an
    absent tier is simply skipped, never a KeyError - or the AMBIGUOUS
    sentinel to force this record into the ambiguous bucket outright.
    """

    tier_name: str
    provide: Callable[[EntryRecord], Optional[tuple[str, ...]]]


# --- tolerant verification -------------------------------------------
#
# Traktor's FILESIZE and PLAYTIME_FLOAT can never equal what the disk
# reports, so neither can take part in an exact key against a candidate.
# Measured against a real 6,386-entry collection and its files:
#
#   FILESIZE vs bytes/1024   median 0.17% error, max 0.41%  (Traktor
#                            records the audio payload, excluding tag and
#                            artwork overhead, so the gap grows with
#                            embedded art)
#   PLAYTIME_FLOAT vs mutagen  median 0.048s error, max 0.172s
#
# They are therefore used to REFUTE a candidate, never to identify one.
#
# CALIBRATION. Those figures come from ONE collection, and neither error is
# a property of the formats - both are properties of that library's files:
#
#   - The size gap is tag and artwork overhead, which is additive and
#     unbounded. A 500 KB cover image on a 5,000 KB track is a 9% gap, not
#     0.41%. The measured maximum says that collection's art is small; it
#     says nothing about anyone else's.
#   - The duration gap is mutagen's estimate, which is exact only when the
#     file carries a Xing/VBRI header. Without one it extrapolates from the
#     first frame and can be 5-10% out on a VBR file - tens of seconds.
#
# So a bound fitted to those maxima rejects correct candidates on any
# library that differs. Cross-source comparison instead uses wide FACTOR
# bands, which is all the evidence actually supports: it still separates a
# 30-second preview from a six-minute track (a factor of twelve) while
# absorbing artwork and VBR estimation, and the module's own priority says
# to err this way - a too-tight bound loses a file the user has, a loose
# one only weakens tie-breaking the tier keys were doing anyway.
#
# Same-source comparison (collection vs collection) keeps the tight bounds:
# there both sides are Traktor's own numbers for the same quantity, so a
# real difference means a genuinely different file.
_SIZE_REL_TOLERANCE = 0.02
_DURATION_ABS_TOLERANCE = 1.0

# Cross-source: a candidate is refuted only outside this factor band, or
# outside the larger of the absolute and relative duration allowances.
_CROSS_SIZE_MIN_FACTOR = 0.25
_CROSS_SIZE_MAX_FACTOR = 4.0
_CROSS_DURATION_REL_TOLERANCE = 0.15

# Tiers whose key IS an identity claim rather than a similarity signal, and
# which therefore outrank the approximate size/duration check entirely.
# AUDIO_ID is Traktor's own content-derived identifier: when it agrees, a
# size difference means the file was re-tagged or had art embedded, not that
# it is a different recording. Letting a cover image veto it would discard
# the strongest evidence the cascade has on the strength of the weakest.
_IDENTITY_TIERS: frozenset[str] = frozenset({"audio_id"})


def _size_kb(record: EntryRecord) -> Optional[float]:
    """Both sides' size in kilobytes, or None when unknown.

    A disk-derived candidate (source_path set) carries the real byte count
    from stat(); a collection record carries Traktor's own KB figure.
    """
    if not record.filesize:
        return None
    try:
        value = float(record.filesize)
    except ValueError:
        return None
    return value / 1024.0 if record.source_path is not None else value


def _duration_seconds(record: EntryRecord) -> Optional[float]:
    if not record.playtime_float:
        return None
    try:
        return float(record.playtime_float)
    except ValueError:
        return None


def _is_cross_source(old_record: EntryRecord, candidate: EntryRecord) -> bool:
    """True when one side is a disk candidate and the other is not.

    Only then do the two sides measure different quantities (payload
    kilobytes vs bytes on disk; Traktor's decode vs mutagen's estimate) and
    need the wide bands.
    """
    return (old_record.source_path is None) != (candidate.source_path is None)


def _refutes(old_record: EntryRecord, candidate: EntryRecord) -> bool:
    """True when size or duration positively contradict the candidate.

    Absent data never refutes: a candidate whose tags could not be read is
    left for the tier keys to judge rather than silently discarded. Nor does
    a difference the comparison cannot attribute - see the calibration note
    above for why the cross-source bands are factor-wide.
    """
    cross = _is_cross_source(old_record, candidate)

    # `is not None`, not truthiness: a zero is a claim (an empty file, a
    # zero-length entry), and one side claiming zero against the other's
    # real value is a contradiction, not missing data. Only the two-zero
    # case is skipped, which would otherwise divide by zero.
    old_kb, new_kb = _size_kb(old_record), _size_kb(candidate)
    if old_kb is not None and new_kb is not None and max(old_kb, new_kb) > 0:
        if cross:
            # Asymmetric in effect as well as wide: overhead only ever makes
            # the file on disk BIGGER, so the upper bound is the loose one.
            if old_kb <= 0 or not (
                _CROSS_SIZE_MIN_FACTOR <= new_kb / old_kb <= _CROSS_SIZE_MAX_FACTOR
            ):
                return True
        elif abs(old_kb - new_kb) / max(old_kb, new_kb) > _SIZE_REL_TOLERANCE:
            return True

    old_s, new_s = _duration_seconds(old_record), _duration_seconds(candidate)
    if old_s is not None and new_s is not None:
        allowance = _DURATION_ABS_TOLERANCE
        if cross:
            # Relative, because mutagen's error on a headerless VBR file
            # scales with track length rather than being a fixed offset.
            allowance = max(allowance, _CROSS_DURATION_REL_TOLERANCE * max(old_s, new_s))
        if abs(old_s - new_s) > allowance:
            return True

    return False


def _path_suffix(record: EntryRecord, depth: int) -> Optional[tuple[str, ...]]:
    """The last `depth` folder names plus the filename, or None if the
    path is too shallow.

    Identifies a file by where it sits relative to its own folders, which
    a wholesale move preserves exactly - the dominant real-world case.
    Comparable from either side: a collection record decodes Traktor's DIR,
    a disk candidate carries its real parent path.
    """
    parts = [part for part in record.location.decoded_dir.parts if part not in ("/", "")]
    if len(parts) < depth or not record.file_name:
        return None
    return tuple(parts[len(parts) - depth:]) + (record.file_name,)


def record_keys(
    record: EntryRecord,
    confidence: MatchConfidence,
    key_providers: Iterable[KeyProvider] = (),
) -> list[tuple[str, tuple[str, ...]]]:
    keys: list[tuple[str, tuple[str, ...]]] = []
    for provider in key_providers:
        value = provider.provide(record)
        if value is not None:
            keys.append((provider.tier_name, value))

    if confidence.admits("audio_id") and record.audio_id:
        keys.append(("audio_id", (record.audio_id,)))
    if (
        confidence.admits("artist_title_size_time")
        and record.artist
        and record.title
        and record.filesize
        and record.playtime_float
    ):
        keys.append(
            (
                "artist_title_size_time",
                (record.artist, record.title, record.filesize, record.playtime_float),
            )
        )
    if confidence.admits("artist_title_file") and record.artist and record.title and record.file_name:
        keys.append(("artist_title_file", (record.artist, record.title, record.file_name)))
    if (
        confidence.admits("file_size_time")
        and record.file_name
        and record.filesize
        and record.playtime_float
    ):
        keys.append(("file_size_time", (record.file_name, record.filesize, record.playtime_float)))
    if (
        confidence.admits("artist_title_album_time")
        and record.artist
        and record.title
        and record.album
        and record.playtime_float
    ):
        keys.append(
            (
                "artist_title_album_time",
                (record.artist, record.title, record.album, record.playtime_float),
            )
        )
    for depth in (3, 2):
        tier = f"path_suffix_{depth}"
        if confidence.admits(tier):
            suffix = _path_suffix(record, depth)
            if suffix is not None:
                keys.append((tier, suffix))
    if confidence.admits("artist_title") and record.artist and record.title:
        keys.append(("artist_title", (record.artist, record.title)))
    if confidence.admits("path_suffix_1"):
        suffix = _path_suffix(record, 1)
        if suffix is not None:
            keys.append(("path_suffix_1", suffix))
    if confidence.admits("filename") and record.file_name:
        keys.append(("filename", (record.file_name,)))
    # There is deliberately no filename_size tier. It keyed on the raw
    # FILESIZE string from both sides, which measure different quantities in
    # different units (Traktor: kilobytes of audio payload; a disk scan:
    # bytes on disk), so any match it produced was a numeric coincidence
    # rather than evidence - and it sat last in the cascade, where its only
    # effect was to break a filename ambiguity by accident. Size now enters
    # through _refutes, where being approximate is sound.
    return keys


def build_new_indexes(
    records: list[EntryRecord],
    confidence: MatchConfidence,
    key_providers: Iterable[KeyProvider] = (),
) -> dict[str, dict[tuple[str, ...], list[EntryRecord]]]:
    indexes: dict[str, dict[tuple[str, ...], list[EntryRecord]]] = defaultdict(lambda: defaultdict(list))
    for record in records:
        for key_name, key_value in record_keys(record, confidence, key_providers):
            indexes[key_name][key_value].append(record)
    return indexes


def _prefer_current_sync_copy(candidates: list[EntryRecord]) -> list[EntryRecord]:
    """Prefer the active Sync_ copy when an identity also has a Sync_old copy.

    This is intentionally limited to the paired path convention used by the
    collection migration. Other duplicate candidate sets remain ambiguous.
    """
    current = [record for record in candidates if "Sync_" in record.location.decoded_dir.parts]
    old = [record for record in candidates if "Sync_old" in record.location.decoded_dir.parts]
    if old and len(current) == 1:
        return current
    return candidates


def match_records(
    old_records: list[EntryRecord],
    new_records: list[EntryRecord],
    confidence: MatchConfidence,
    key_providers: Iterable[KeyProvider] = (),
    indexes: dict[str, dict[tuple[str, ...], list[EntryRecord]]] | None = None,
) -> tuple[dict[str, EntryRecord], dict[str, int], list[tuple[str, str, str, str]]]:
    # A caller that already built the candidate index for its own purposes
    # (e.g. reconnection's post-match ambiguity check) can pass it in so the
    # O(candidates) index build never runs twice for one match_records call.
    if indexes is None:
        indexes = build_new_indexes(new_records, confidence, key_providers)
    mapping: dict[str, EntryRecord] = {}
    # The six tag-derived tiers always get a stats key, matching every
    # pre-extraction stats dict exactly regardless of confidence (the
    # confidence level gates whether a tier can produce a match, not whether
    # its counter is printed). The path-suffix tiers and any injected
    # provider tier are later additions with no such baseline to
    # preserve, so they only appear when actually reachable at this
    # confidence / with providers supplied - a counter for a tier that
    # cannot fire reads as "tried and found nothing", which is a lie.
    tier_names = [p.tier_name for p in key_providers] + list(_BASE_STAT_TIERS)
    tier_names += [name for name in _EXTRA_STAT_TIERS if confidence.admits(name)]
    # `refuted` counts old records that ended unmatched WITH a candidate the
    # size/duration check removed. Without it a refusal to commit is
    # indistinguishable in the stats from a file that is genuinely gone, and
    # the operator reads "the tool found nothing" when the truth is "the tool
    # found something and declined it". This is the same distinction DL-016
    # added `destination_collisions` for on the one-to-one post-pass.
    stats = {
        "matched": 0,
        **{f"matched_{name}": 0 for name in tier_names},
        "unmatched": 0,
        "refuted": 0,
        "ambiguous": 0,
    }
    samples: list[tuple[str, str, str, str]] = []

    for old_record in old_records:
        matched_new: EntryRecord | None = None
        matched_by: str | None = None
        ambiguous_here = False
        refuted_here = False

        for key_name, key_value in record_keys(old_record, confidence, key_providers):
            if key_value is AMBIGUOUS:
                # A provider positively detected its own unresolvable
                # multi-candidate conflict (see AMBIGUOUS) - the record is
                # ambiguous outright, and no lower, less specific tier is
                # allowed to silently resolve it to a single confident
                # match, so no further tiers are consulted for this record.
                ambiguous_here = True
                break
            candidates = indexes.get(key_name, {}).get(key_value, [])
            # Prefer BEFORE refuting, not after. Refutation can remove the
            # active Sync_ copy - which, being the one a migration is
            # rewriting, is the copy most likely to have drifted in size -
            # and that would leave the stale Sync_old copy alone in the list,
            # where it matches cleanly and is reported as a success. Choosing
            # the preferred copy first means a refuted current copy yields no
            # match at all, which is the honest outcome.
            candidates = _prefer_current_sync_copy(candidates)
            if key_name not in _IDENTITY_TIERS:
                # Refute before counting: a size or duration contradiction
                # removes a candidate, so a tier with one plausible and one
                # implausible hit resolves cleanly instead of reporting a
                # false ambiguity the operator would have to adjudicate.
                kept = [c for c in candidates if not _refutes(old_record, c)]
                if len(kept) != len(candidates):
                    refuted_here = True
                candidates = kept
            if len(candidates) == 1:
                matched_new = candidates[0]
                matched_by = key_name
                break
            if len(candidates) > 1:
                ambiguous_here = True

        if matched_new is not None and matched_by is not None:
            mapping[old_record.primary_key] = matched_new
            stats["matched"] += 1
            stats[f"matched_{matched_by}"] += 1
            if len(samples) < 20:
                samples.append(
                    (
                        record_label(old_record),
                        str(old_record.location.decoded_path),
                        str(matched_new.location.decoded_path),
                        matched_by,
                    )
                )
        elif ambiguous_here:
            stats["ambiguous"] += 1
        else:
            stats["unmatched"] += 1
            # A subset of unmatched, not a separate bucket: the record is
            # still unmatched, but the operator can now tell that a candidate
            # was found and declined rather than never found at all.
            if refuted_here:
                stats["refuted"] += 1

    return mapping, stats, samples
