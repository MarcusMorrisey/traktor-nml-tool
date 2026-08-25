"""Ordered match-confidence levels shared by every matching-cascade caller.

Disk-scan matching needs a filename-only tier the legacy boolean cannot
express, and two overlapping knobs would let two flags fight over one
cascade. MatchConfidence is a single ordered ladder instead: strict admits
the tag-derived tiers down to file/size/time plus the deep path-suffix
tiers, loose additionally admits artist/title/album/time, the legacy
artist-title-only tier and the shallow one-folder path suffix, and filename
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
# legacy artist-title-only one) plus the deep path-suffix tiers; loose
# additionally admits the legacy tier, matching --allow-artist-title-only bit
# for bit, and the shallow one-folder suffix; filename adds the disk-scan-only
# tiers that need no tags at all.
#
# The path-suffix tiers sit at strict because they are highly discriminating
# rather than merely permissive: measured over a real 6,386-entry collection,
# a three-folder suffix is unique for 97.2% of entries. They also survive the
# case the tag tiers cannot - a wholesale move of a library, which changes
# every absolute path but preserves each file's position within its own
# folders. path_suffix_1 is the one shallow enough to collide across sibling
# libraries ("Album/track01.mp3"), so it waits for loose.
_STRICT_TIERS: tuple[str, ...] = (
    "audio_id",
    "artist_title_size_time",
    "artist_title_file",
    "file_size_time",
    "artist_title_album_time",
    "path_suffix_3",
    "path_suffix_2",
)
_LOOSE_TIERS: tuple[str, ...] = _STRICT_TIERS + ("artist_title", "path_suffix_1")
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
