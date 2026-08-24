"""Ordered match-confidence levels shared by every matching-cascade caller.

Disk-scan matching needs a filename-only tier the legacy boolean cannot
express, and two overlapping knobs would let two flags fight over one
cascade. MatchConfidence is a single ordered ladder instead: strict admits
only the tag-derived tiers down to file/size/time, loose additionally admits
artist/title/album/time and the legacy artist-title-only tier, and filename
additionally admits a filename-only tier for disk candidates whose tags are
unreadable. --allow-artist-title-only keeps parsing as loose so existing
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
# strict reproduces the pre-extraction default cascade exactly (every tier
# except the legacy artist-title-only one); loose additionally admits that
# tier, matching --allow-artist-title-only bit for bit; filename adds the
# disk-scan-only filename+size tier that has no tag-based fallback at all.
_STRICT_TIERS: tuple[str, ...] = (
    "audio_id",
    "artist_title_size_time",
    "artist_title_file",
    "file_size_time",
    "artist_title_album_time",
)
_LOOSE_TIERS: tuple[str, ...] = _STRICT_TIERS + ("artist_title",)
_FILENAME_TIERS: tuple[str, ...] = _LOOSE_TIERS + ("filename_size",)

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
