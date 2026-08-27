"""Disk-scan reconnection: match old collection records against candidates.

match_records only detects source-side ambiguity - several candidates for
one old track - and returns a plain old-to-new mapping. Two distinct old
entries can each match the same physical file unambiguously on their own and
both be marked matched, which would point two collection entries and their
playlist references at one LOCATION. resolve_reconnection inverts the
mapping after matching completes: any candidate holding more than one
assignment removes all of its claimants, counted under destination
collisions and exported to the ambiguity CSV instead of being rewritten
(DL-004). The returned mapping is therefore strictly one-to-one.
"""

# DL-004 is enforced purely as a post-match inversion pass; match_records
# is unaware that a one-to-one guarantee is layered on top of its plain
# old-to-new mapping.

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Callable, Optional

from .confidence import MatchConfidence
from .matching import AMBIGUOUS, KeyProvider, build_new_indexes, match_records, record_keys
from .model import EntryRecord, LocationParts, encode_traktor_dir
from .review import RecordReview


def location_from_disk_path(path: Path, volume: str, volumeid: str) -> LocationParts:
    """Invert decode_traktor_dir: an absolute disk path plus a resolved
    volume identity becomes a LOCATION whose DIR carries the Traktor
    separator encoding and whose FILE is the path's final component.

    DIR must be volume-relative, the way every real LOCATION in a Traktor
    collection is (e.g. VOLUME="Macintosh HD" DIR="/:Users/:freqking/:...",
    never carrying the OS mount point itself) - only path's own anchor (the
    drive letter or POSIX root, e.g. "D:\\" or "/") is stripped before
    encoding. A scan root (e.g. D:\\Music\\Techno) is an arbitrary
    user-supplied subdirectory, not the volume's actual root; stripping it
    instead of the anchor would drop every intermediate path segment between
    the volume root and the scan root from the rewritten DIR, so DIR would
    never reconstruct the file's real volume-relative path.
    """
    anchor = path.anchor
    relative_dir = path.parent.relative_to(anchor) if anchor else path.parent
    relative_str = "" if str(relative_dir) == "." else str(relative_dir)
    return LocationParts(
        volume=volume,
        volumeid=volumeid,
        dir_value="/:" if not relative_str else encode_traktor_dir(relative_str),
        file_name=path.name,
    )


def enforce_one_to_one(
    mapping: dict[str, EntryRecord],
    match_stats: dict[str, int],
    old_records: list[EntryRecord],
    indexes: dict[str, dict[tuple[str, ...], list[EntryRecord]]],
    confidence: MatchConfidence,
    key_providers: list[KeyProvider] = (),
) -> tuple[dict[str, EntryRecord], dict[str, int], set[str]]:
    """Invert mapping (a plain old-to-new mapping from match_records) to
    find candidates claimed by more than one old record, drop every
    claimant, re-derive each affected tier's match count, and return the
    pruned mapping, the corrected stats (carrying destination_collisions
    and matched), and the set of dropped old keys (DL-004).

    This is the one shared implementation of the one-to-one guarantee:
    resolve_reconnection and rewrite_from_collection_compare both call it
    rather than each re-deriving their own inversion pass.
    """
    records_by_key = {record.primary_key: record for record in old_records}
    dest_claimants: dict[int, list[str]] = {}
    for old_key, candidate in mapping.items():
        dest_claimants.setdefault(id(candidate), []).append(old_key)
    collided_keys = {key for claimants in dest_claimants.values() if len(claimants) > 1 for key in claimants}

    # A withdrawn destination collision was still counted under its match
    # tier when match_records ran; re-derive that tier the same way
    # match_records did (first tier whose index bucket holds exactly this
    # one candidate) so matched_<tier> stays consistent with the final
    # matched total instead of overcounting a match that was later undone.
    stats = dict(match_stats)
    for old_key in collided_keys:
        record = records_by_key.get(old_key)
        if record is None:
            continue
        winner = mapping[old_key]
        for key_name, key_value in record_keys(record, confidence, key_providers):
            if indexes.get(key_name, {}).get(key_value) == [winner]:
                stat_name = f"matched_{key_name}"
                if stat_name in stats:
                    stats[stat_name] -= 1
                break

    final_mapping = {key: value for key, value in mapping.items() if key not in collided_keys}
    stats["destination_collisions"] = len(collided_keys)
    stats["matched"] = len(final_mapping)
    return final_mapping, stats, collided_keys


def resolve_reconnection(
    old_records: list[EntryRecord],
    candidates: list[EntryRecord],
    confidence: MatchConfidence,
    key_providers: list[KeyProvider] = (),
    refute: bool = True,
    on_review: Optional[Callable[[RecordReview], None]] = None,
) -> tuple[dict[str, EntryRecord], dict[str, int], list[dict[str, str]]]:
    """Match old_records against candidates via the shared cascade, then
    invert the resulting mapping to find and drop destination collisions
    - candidates claimed by more than one old record - reclassifying
    their claimants out of the one-to-one mapping and re-deriving each
    affected tier's match count so matched_<tier> totals stay consistent
    with the final matched count (DL-004).

    on_review defaults to None and is forwarded to match_records with
    nothing else changed, so a caller supplying nothing gets the identical
    mapping, stats and ambiguity_rows this function has always returned.
    When supplied, the reviews match_records emits are held here rather
    than handed straight to the caller, because the one-to-one guarantee
    match_records is deliberately unaware of (see the module docstring)
    is not resolved until enforce_one_to_one runs below: a review is
    reclassified to destination_collision in the same walk that already
    builds ambiguity_rows for every collided key, then on_review is called
    for each review in the order match_records produced them.
    """
    # Built once and reused both for match_records' own lookup and for the
    # post-match ambiguity check below, instead of match_records building
    # its own copy and this function silently rebuilding an identical one
    # (doubling the O(old x candidates) fingerprint similarity search when a
    # fingerprint provider is injected).
    indexes = build_new_indexes(candidates, confidence, key_providers)
    reviews: list[RecordReview] | None = [] if on_review is not None else None
    mapping, match_stats, _samples = match_records(
        old_records,
        candidates,
        confidence,
        key_providers,
        indexes=indexes,
        refute=refute,
        on_review=None if reviews is None else reviews.append,
    )

    final_mapping, stats, collided_keys = enforce_one_to_one(
        mapping, match_stats, old_records, indexes, confidence, key_providers
    )

    if reviews is not None:
        for index, review in enumerate(reviews):
            if review.old.primary_key in collided_keys:
                reviews[index] = replace(review, status="destination_collision")
        for review in reviews:
            on_review(review)

    ambiguity_rows: list[dict[str, str]] = []
    for record in old_records:
        old_key = record.primary_key
        if old_key in final_mapping:
            continue
        if old_key in collided_keys:
            reason = "destination_collision"
        else:
            # value is AMBIGUOUS whenever a provider (see matching.AMBIGUOUS)
            # positively detected its own unresolvable multi-candidate
            # conflict for this record - that conflict never appears as an
            # index bucket of size > 1, since nothing else shares the
            # provider's own internal comparison, so it must be checked for
            # directly alongside the ordinary bucket-size ambiguity check.
            ambiguous_here = any(
                value is AMBIGUOUS or len(indexes.get(name, {}).get(value, [])) > 1
                for name, value in record_keys(record, confidence, key_providers)
            )
            reason = "ambiguous" if ambiguous_here else "unmatched"
        ambiguity_rows.append(
            {
                "artist": record.artist,
                "title": record.title,
                "old_path": str(record.location.decoded_path),
                "reason": reason,
            }
        )

    return final_mapping, stats, ambiguity_rows
