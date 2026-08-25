"""Ordered match-confidence levels shared by every matching-cascade caller.

Disk-scan matching needs a filename-only tier the legacy boolean cannot
express, and two overlapping knobs would let two flags fight over one
cascade. MatchConfidence is a single ordered ladder instead: strict admits
the tag-derived tiers down to file/size/time plus the deep three-folder
path suffix, loose additionally admits artist/title/album/time, the legacy
artist-title-only tier and the two shallower path suffixes, and filename
additionally admits the bare-filename tiers for disk candidates whose tags
are unreadable. --allow-artist-title-only keeps parsing as loose so existing
invocations are unaffected.
"""

from __future__ import annotations

import enum


class MatchConfidence(enum.Enum):
    STRICT = "strict"
    LOOSE = "loose"
    FILENAME = "filename"

    @classmethod
    def from_legacy_flag(cls, allow_artist_title_only: bool) -> "MatchConfidence":
        """--allow-artist-title-only maps to LOOSE: kept as a stable
        spelling for scripted invocations that predate this ordered
        enum (DL-010)."""
        return cls.LOOSE if allow_artist_title_only else cls.STRICT

    def admits(self, tier_name: str) -> bool:
        return tier_name in self.admitted_tiers()

    def admitted_tiers(self) -> tuple[str, ...]:
        return _ADMITTED_TIERS[self]


# Tier names match the key_name strings record_keys emits. Each level admits
# every tier of the level below it plus its own additions, so widening the
# confidence argument never removes a tier a stricter run already accepted.
# strict reproduces the pre-extraction default cascade (every tier except the
# legacy artist-title-only one) plus the deep three-folder path suffix; loose
# additionally admits the legacy tier, matching --allow-artist-title-only bit
# for bit, and the two shallower path suffixes; filename adds the
# disk-scan-only tier that needs no tags at all.
#
# path_suffix_3 sits at strict because it is highly discriminating rather
# than merely permissive: measured over a real 6,386-entry collection, a
# three-folder suffix is unique for 97.2% of entries. It also survives the
# case the tag tiers cannot - a wholesale move of a library, which changes
# every absolute path but preserves each file's position within its own
# folders.
#
# The shallower two wait for loose, and the reason is that 97.2% is a
# measurement of DEPTH THREE only. Nothing was measured at depth two, and it
# is not a small extrapolation: dropping a folder drops the album or release
# level, so ("CD1", "01 - Intro.mp3") recurs across every multi-disc release
# that uses that layout, and ("Album", "track01.mp3") across sibling
# libraries. Colliding keys report ambiguity rather than a wrong match, so
# the cost is the operator's time - but strict is the default and the level
# a cautious operator reaches for, and it should not be where an unmeasured
# tier makes them adjudicate. Measure depth two on a real collection and
# path_suffix_2 can move up on evidence.
_STRICT_TIERS: tuple[str, ...] = (
    "audio_id",
    "artist_title_size_time",
    "artist_title_file",
    "file_size_time",
    "artist_title_album_time",
    "path_suffix_3",
)
_LOOSE_TIERS: tuple[str, ...] = _STRICT_TIERS + ("artist_title", "path_suffix_2", "path_suffix_1")
_FILENAME_TIERS: tuple[str, ...] = _LOOSE_TIERS + ("filename",)

_ADMITTED_TIERS = {
    MatchConfidence.STRICT: _STRICT_TIERS,
    MatchConfidence.LOOSE: _LOOSE_TIERS,
    MatchConfidence.FILENAME: _FILENAME_TIERS,
}


def parse_match_confidence(value: str) -> MatchConfidence:
    try:
        return MatchConfidence(value)
    except ValueError as exc:
        valid = ", ".join(level.value for level in MatchConfidence)
        raise ValueError(f"invalid --match-confidence {value!r}; expected one of: {valid}") from exc
