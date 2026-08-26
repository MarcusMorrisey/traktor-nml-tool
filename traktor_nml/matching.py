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

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from .confidence import MatchConfidence
from .model import EntryRecord, record_label

@dataclass(frozen=True)
class _TierSpec:
    """One built-in cascade tier and the properties other code asks about it.

    Before this table the same ten tier names were listed in five separate
    string tuples - the confidence ladder, the two stats tuples, the identity
    exemption, and the emission order in record_keys - each hand-kept in step
    with the others and none of them checked against the rest. The properties
    belong to the tier, so they live on the tier; the ladder in confidence.py
    is the one remaining separate listing, and a test asserts the two agree.
    """

    name: str
    # True for the six tiers whose stats key predates the parity baseline and
    # is therefore emitted whatever the confidence. The rest appear only when
    # the run's confidence admits them - a counter for a tier that cannot fire
    # reads as "tried and found nothing", which is a lie.
    always_seed_stat: bool
    # False for a tier whose key IS an identity claim rather than a similarity
    # signal. AUDIO_ID is Traktor's own content-derived identifier: when it
    # agrees, a size difference means the file was re-tagged or re-encoded, so
    # letting the approximate size check veto it would discard the strongest
    # evidence the cascade has on the strength of the weakest (DL-042).
    refutable: bool = True
    # True for a tier that keys only on path or filename, and so still works
    # when no tags can be read. diskscan.py derives its mutagen-absent
    # diagnostic from this rather than naming tiers in prose that goes stale.
    tag_free: bool = False


# Cascade order: record_keys emits in exactly this sequence, strongest first.
_CASCADE: tuple[_TierSpec, ...] = (
    _TierSpec("audio_id", always_seed_stat=True, refutable=False),
    _TierSpec("artist_title_size_time", always_seed_stat=True),
    _TierSpec("artist_title_file", always_seed_stat=True),
    _TierSpec("file_size_time", always_seed_stat=True),
    _TierSpec("artist_title_album_time", always_seed_stat=True),
    _TierSpec("path_suffix_3", always_seed_stat=False, tag_free=True),
    _TierSpec("path_suffix_2", always_seed_stat=False, tag_free=True),
    _TierSpec("artist_title", always_seed_stat=True),
    _TierSpec("path_suffix_1", always_seed_stat=False, tag_free=True),
    _TierSpec("bare_name_in_folder", always_seed_stat=False, tag_free=True),
    _TierSpec("filename", always_seed_stat=False, tag_free=True),
    _TierSpec("bare_name", always_seed_stat=False, tag_free=True),
)

_TIERS_BY_NAME: dict[str, _TierSpec] = {tier.name: tier for tier in _CASCADE}


def _is_refutable(tier_name: str) -> bool:
    """Injected provider tiers (DL-006) are not in the table and refute like
    any similarity tier; only a declared identity tier is exempt."""
    tier = _TIERS_BY_NAME.get(tier_name)
    return tier is None or tier.refutable


def tag_free_tiers(confidence: MatchConfidence) -> tuple[str, ...]:
    """Tiers this confidence admits that need no readable tags.

    Exported so a caller reporting degraded matching names what actually
    remains rather than repeating a hardcoded list that rots when a tier
    changes level.
    """
    return tuple(t.name for t in _CASCADE if t.tag_free and confidence.admits(t.name))


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


def _size_kb(record: EntryRecord) -> Optional[float]:
    """The record's size in kilobytes, or None when unknown.

    Both sides already carry kilobytes: a collection record holds Traktor's
    own FILESIZE, and diskscan converts stat()'s byte count at construction.
    Deliberately no provenance branch here - inferring the unit from another
    field would fail silently by a factor of 1024 on any record that did not
    happen to set it.
    """
    if not record.filesize:
        return None
    try:
        return float(record.filesize)
    except ValueError:
        return None


def _duration_seconds(record: EntryRecord) -> Optional[float]:
    if not record.playtime_float:
        return None
    try:
        return float(record.playtime_float)
    except ValueError:
        return None


class _Claims:
    """One record's size and duration, parsed once.

    match_records refutes every candidate in every tier bucket against the
    same old record, so parsing that record's two fields inside the check
    re-did identical float() work once per candidate per tier - tens of
    thousands of times over a full collection. The old side is parsed once
    per record and carried; only the candidate side is parsed per call.
    """

    __slots__ = ("size_kb", "seconds", "from_disk")

    def __init__(self, record: EntryRecord) -> None:
        self.size_kb = _size_kb(record)
        self.seconds = _duration_seconds(record)
        self.from_disk = record.source_path is not None


def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
    """True when duration positively contradicts the candidate.

    Absent data never refutes: a candidate whose tags could not be read is
    left for the tier keys to judge rather than silently discarded. Size
    refutes only when both sides come from the same source; across sources
    it is corroboration only, for the reasons set out below.
    """
    new = _Claims(candidate)
    # Only when one side is disk-derived and the other is not do the two
    # sides measure different quantities and need the wide bands.
    cross = old.from_disk != new.from_disk

    # `is not None`, not truthiness: a zero is a claim (an empty file, a
    # zero-length entry), and one side claiming zero against the other's
    # real value is a contradiction, not missing data. Only the two-zero
    # case is skipped, which would otherwise divide by zero.
    old_kb, new_kb = old.size_kb, new.size_kb
    if not cross and old_kb is not None and new_kb is not None and max(old_kb, new_kb) > 0:
        # SAME-SOURCE ONLY. Both sides are then Traktor's own figure for the
        # same quantity, so a real difference means a genuinely different
        # file.
        #
        # Cross-source, size deliberately does NOT refute at all. A DJ's
        # library legitimately holds the same track at many sizes over time:
        # upgraded to STEMS, re-encoded to WAV for a performance, downgraded
        # to reclaim drive space. Measured over 91 same-name/different-format
        # pairs in a real collection, disk/collection size spans 0.23x to
        # 49.22x - a 0.23x downgrade and a 4.44x WAV upgrade both sat outside
        # the factor band this check used to apply, so it silently rejected
        # exactly the cases a DJ creates on purpose. Size disagreement
        # carries almost no negative information.
        #
        # Duration is the format-invariant: a transcode preserves length and
        # changes bytes. Over those same 91 pairs it differs by a median of
        # 0.110s (p95 0.171s), while a genuinely different recording stood
        # out at 3,087s. So duration refutes and size does not.
        #
        # Size still earns its keep as POSITIVE evidence - see
        # _size_agrees, which breaks ambiguity rather than creating it.
        if abs(old_kb - new_kb) / max(old_kb, new_kb) > _SIZE_REL_TOLERANCE:
            return True

    old_s, new_s = old.seconds, new.seconds
    if old_s is not None and new_s is not None:
        allowance = _DURATION_ABS_TOLERANCE
        if cross:
            # Relative, because mutagen's error on a headerless VBR file
            # scales with track length rather than being a fixed offset.
            allowance = max(allowance, _CROSS_DURATION_REL_TOLERANCE * max(old_s, new_s))
        if abs(old_s - new_s) > allowance:
            return True

    return False


def _size_agrees(old: _Claims, candidate: EntryRecord) -> bool:
    """True when both sides report effectively the same size.

    The positive half of the rule above. Size cannot refute across sources,
    but agreement to within a fraction of a percent is strong evidence that
    two files are the same bytes rather than the same track in a different
    encoding - so it is used to settle an ambiguity a tier could not settle
    alone, never to discard a candidate.
    """
    new = _Claims(candidate)
    old_kb, new_kb = old.size_kb, new.size_kb
    if old_kb is None or new_kb is None or max(old_kb, new_kb) <= 0:
        return False
    return abs(old_kb - new_kb) / max(old_kb, new_kb) <= _SIZE_REL_TOLERANCE


def _refutes(old_record: EntryRecord, candidate: EntryRecord) -> bool:
    """Single-pair form of _claims_refute, for callers outside the match loop."""
    return _claims_refute(_Claims(old_record), candidate)


def _folder_parts(record: EntryRecord) -> tuple[str, ...]:
    """The record's folder names, anchor stripped.

    Decoding a DIR allocates a fresh PurePosixPath, and the three path-suffix
    depths all want the same list, so record_keys computes this once and
    slices it rather than calling per depth.
    """
    return tuple(part for part in record.location.decoded_dir.parts if part not in ("/", ""))


def _path_suffix_from(parts: tuple[str, ...], file_name: str, depth: int) -> Optional[tuple[str, ...]]:
    """The last `depth` folder names plus the filename, or None if the
    path is too shallow.

    Identifies a file by where it sits relative to its own folders, which
    a wholesale move preserves exactly - the dominant real-world case.
    Comparable from either side: a collection record decodes Traktor's DIR,
    a disk candidate carries its real parent path.
    """
    if len(parts) < depth or not file_name:
        return None
    # Folded like every other key component: a folder renamed only in
    # capitalisation is the same folder to the filesystem (see _fold).
    return tuple(_fold(part) for part in parts[len(parts) - depth:]) + (_fold(file_name),)


def _path_suffix(record: EntryRecord, depth: int) -> Optional[tuple[str, ...]]:
    """Single-record form, for callers outside record_keys."""
    return _path_suffix_from(_folder_parts(record), record.file_name, depth)


_FORMAT_SUFFIX = re.compile(r"(\.stem)?\.[A-Za-z0-9]{1,5}$")


def _bare_name(file_name: str) -> Optional[str]:
    """A file name with its container format stripped, folded for comparison.

    "track.mp3", "track.wav" and "track.stem.m4a" all reduce to "track".

    A DJ's library holds one track in several encodings across its life,
    deliberately: upgraded to STEMS, re-encoded to WAV for a performance,
    downgraded to reclaim drive space. Each of those REPLACES the file
    rather than moving it, so every tier keying on the name as written -
    filename, and the path suffixes, which end in it - stops matching, and
    the entry is reported as though the track were gone. Measured on a real
    collection, 61 stem upgrades whose replacement sat on the same drive
    matched at no confidence level at all.

    The ".stem" infix is stripped as well as the extension because Traktor
    stem files are named "track.stem.m4a"; without it a stem upgrade would
    reduce to "track.stem" and still miss.
    """
    if not file_name:
        return None
    bare = _FORMAT_SUFFIX.sub("", file_name)
    return _fold(bare) if bare else None


def _fold(value: str) -> str:
    """Casefold one key component for comparison.

    Every tier below keys on text drawn from two independent sources - a
    collection's ARTIST/TITLE attributes and a file's tags or path - and
    the same track routinely differs between them only in capitalisation:
    measured on a real 6,412-entry collection, eight otherwise-perfect
    matches were lost to exactly that (Medjula/MeDJula,
    "We Like to Party"/"We like to Party", McNAiR/MCNAiR). Windows and
    macOS filesystems are case-insensitive, so those name pairs denote the
    SAME file; comparing them byte-for-byte manufactures a difference the
    filesystem does not have.

    casefold rather than lower, because it implements full Unicode case
    folding and so matches the case-insensitivity macOS actually applies.

    Folding is safe here because record_keys' output is only ever compared
    against other record_keys output - nothing downstream reads a key back
    as a display value. AUDIO_ID is deliberately NOT folded: it is
    base64, where case is significant, and folding it would merge
    genuinely distinct identities.

    The failure this can introduce is the safe one: two different tracks
    differing only in case now collide into an ambiguity the operator
    adjudicates, rather than one silently winning.
    """
    return value.casefold()


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
                (_fold(record.artist), _fold(record.title), record.filesize, record.playtime_float),
            )
        )
    if confidence.admits("artist_title_file") and record.artist and record.title and record.file_name:
        keys.append(("artist_title_file", (_fold(record.artist), _fold(record.title), _fold(record.file_name))))
    if (
        confidence.admits("file_size_time")
        and record.file_name
        and record.filesize
        and record.playtime_float
    ):
        keys.append(("file_size_time", (_fold(record.file_name), record.filesize, record.playtime_float)))
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
                (_fold(record.artist), _fold(record.title), _fold(record.album), record.playtime_float),
            )
        )
    # Decoded once and sliced three times: the depths are nested, and each
    # _folder_parts call re-parses the same DIR into a new PurePosixPath.
    folder_parts = _folder_parts(record)

    def _suffix_key(depth: int) -> None:
        tier = f"path_suffix_{depth}"
        if not confidence.admits(tier):
            return
        suffix = _path_suffix_from(folder_parts, record.file_name, depth)
        if suffix is not None:
            keys.append((tier, suffix))

    _suffix_key(3)
    _suffix_key(2)
    if confidence.admits("artist_title") and record.artist and record.title:
        keys.append(("artist_title", (_fold(record.artist), _fold(record.title))))
    # Depth 1 is emitted BELOW artist_title, not with the other two, because
    # a single folder plus filename is weaker evidence than agreeing artist
    # and title. The cascade is ordered by strength, so the split is the
    # point rather than an oversight - see _CASCADE for the authoritative
    # sequence.
    _suffix_key(1)
    # Format-change tiers. Placed below the tiers that key on the name as
    # written, so an exact name match always wins first; these only fire
    # when the file was re-encoded. Duration still refutes, which is what
    # keeps them safe - size deliberately does not (see _claims_refute).
    bare = _bare_name(record.file_name)
    if confidence.admits("bare_name_in_folder") and bare and folder_parts:
        keys.append(("bare_name_in_folder", (_fold(folder_parts[-1]), bare)))
    if confidence.admits("filename") and record.file_name:
        keys.append(("filename", (_fold(record.file_name),)))
    if confidence.admits("bare_name") and bare:
        keys.append(("bare_name", (bare,)))
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
    refute: bool = True,
) -> tuple[dict[str, EntryRecord], dict[str, int], list[tuple[str, str, str, str]]]:
    """refute=False disables the size/duration contradiction filter.

    The filter's tolerances are calibrated against one real collection, so a
    library that breaks an assumption behind them loses correct candidates
    with no way to overrule it from outside this module. That is what the
    switch is for; it is not a general-purpose knob, and the default stays
    on because a contradiction is usually real."""
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
    # Seed order is providers, then the always-seeded tiers, then the rest -
    # not cascade order. That split is historical (the first six tiers'
    # stats keys were pinned by the parity baseline before the others
    # existed), which is why it is expressed as a filter over the one
    # cascade table rather than as a second table listing the same names.
    tier_names = [p.tier_name for p in key_providers]
    tier_names += [t.name for t in _CASCADE if t.always_seed_stat]
    tier_names += [t.name for t in _CASCADE if not t.always_seed_stat and confidence.admits(t.name)]
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
        old_claims = _Claims(old_record)
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
            if refute and _is_refutable(key_name):
                # Refute before counting: a size or duration contradiction
                # removes a candidate, so a tier with one plausible and one
                # implausible hit resolves cleanly instead of reporting a
                # false ambiguity the operator would have to adjudicate.
                kept = [c for c in candidates if not _claims_refute(old_claims, c)]
                if len(kept) != len(candidates):
                    refuted_here = True
                candidates = kept
            if len(candidates) > 1:
                # Size as POSITIVE evidence, the only role it has across
                # sources: when a tier cannot separate its candidates on its
                # own, one whose size agrees to within a fraction of a
                # percent is very likely the same bytes, while the others
                # are at best the same track re-encoded. Applied only when
                # exactly one agrees - two agreeing, or none, leaves the
                # ambiguity for the operator rather than inventing a winner.
                agreeing = [c for c in candidates if _size_agrees(old_claims, c)]
                if len(agreeing) == 1:
                    candidates = agreeing
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
