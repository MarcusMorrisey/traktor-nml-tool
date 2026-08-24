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
    if confidence.admits("artist_title") and record.artist and record.title:
        keys.append(("artist_title", (record.artist, record.title)))
    if confidence.admits("filename_size") and record.file_name and record.filesize:
        keys.append(("filename_size", (record.file_name, record.filesize)))
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
    # its counter is printed). filename_size and any injected provider tier
    # are new additions with no baseline to preserve, so they only appear
    # when actually reachable at this confidence / with providers supplied.
    tier_names = [p.tier_name for p in key_providers] + list(_BASE_STAT_TIERS)
    if confidence is MatchConfidence.FILENAME:
        tier_names.append("filename_size")
    stats = {"matched": 0, **{f"matched_{name}": 0 for name in tier_names}, "unmatched": 0, "ambiguous": 0}
    samples: list[tuple[str, str, str, str]] = []

    for old_record in old_records:
        matched_new: EntryRecord | None = None
        matched_by: str | None = None
        ambiguous_here = False

        for key_name, key_value in record_keys(old_record, confidence, key_providers):
            if key_value is AMBIGUOUS:
                # A provider positively detected its own unresolvable
                # multi-candidate conflict (see AMBIGUOUS) - the record is
                # ambiguous outright, and no lower, less specific tier is
                # allowed to silently resolve it to a single confident
                # match, so no further tiers are consulted for this record.
                ambiguous_here = True
                break
            candidates = _prefer_current_sync_copy(indexes.get(key_name, {}).get(key_value, []))
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

    return mapping, stats, samples
