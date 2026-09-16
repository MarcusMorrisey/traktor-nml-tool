"""External track-list parsing and per-candidate collection resolution.

build-playlist hands resolution one ordered list of Candidate values
(DL-274). A Candidate carries the entry's position and text for the
report, and either the EntryRecord the matching cascade reads as its old
side or None for an entry that could not be parsed. resolve_candidates
resolves that list against a base collection through matching.py at
MatchConfidence.LOOSE (DL-276), candidates on the old side and the
collection on the new (DL-278).

A plain-text track list holds one 'Artist - Title' line per line; each
parsed line becomes a record carrying artist and title only, so the only
tier it reaches is artist_title, since every field the stricter tiers
require (filesize, playtime_float, file_name, album) is empty for a
parsed line. matching.py and confidence.py are imported and called here,
never edited or wrapped in a subclass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .confidence import MatchConfidence
from .matching import build_new_indexes, match_records
from .model import EntryRecord, LocationParts

# A leading track-number prefix ("1 - Artist - Title") uses the same " - "
# delimiter as the artist/title split itself, so it is stripped first -
# otherwise the number consumes the artist slot and the real split shifts
# one delimiter to the right. Digits only (no trailing letters), so an
# artist name that merely starts with a digit (e.g. "2Pac") never matches.
_TRACK_NUMBER_PREFIX_RE = re.compile(r"^\d+\s*-\s*")


@dataclass(frozen=True)
class ParsedLine:
    line_number: int
    raw_text: str
    artist: str
    title: str


@dataclass(frozen=True)
class UnparseableLine:
    line_number: int
    raw_text: str


def parse_tracklist(text: str) -> tuple[list[ParsedLine], list[UnparseableLine]]:
    """Split text into ordered parsed and unparseable lines.

    A blank line (after stripping) or a line starting with '#' is skipped
    entirely. A leading numeric track-number prefix ("1 - Artist - Title")
    is stripped before splitting. The remaining content splits on its first
    ' - ' occurrence into artist (left, stripped) and title (right,
    stripped); a line with no such occurrence, or with an empty half after
    stripping, becomes an unparseable record carrying its 1-based line
    number and raw text instead of being discarded.
    """
    parsed: list[ParsedLine] = []
    unparseable: list[UnparseableLine] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        content = _TRACK_NUMBER_PREFIX_RE.sub("", stripped, count=1)
        # search and slice the same string (DL-031's original bug was
        # searching in one string but slicing another, shifting the split)
        delimiter_idx = content.find(" - ")
        if delimiter_idx < 0:
            unparseable.append(UnparseableLine(line_number=line_number, raw_text=raw_line))
            continue
        artist = content[:delimiter_idx].strip()
        title = content[delimiter_idx + len(" - "):].strip()
        if not artist or not title:
            unparseable.append(UnparseableLine(line_number=line_number, raw_text=raw_line))
            continue
        parsed.append(ParsedLine(line_number=line_number, raw_text=raw_line, artist=artist, title=title))
    return parsed, unparseable


def tracklist_record(line: ParsedLine) -> EntryRecord:
    """Turn one parsed tracklist line into an EntryRecord suitable as the
    matching cascade's old side: entry None, source_path None, artist and
    title from the parsed line, and every remaining identity field the
    empty string, with an empty LocationParts. The empty fields confine
    record_keys to the artist_title tier, and the empty location is never
    read as an authoritative VOLUME/VOLUMEID source, matching how a
    disk-scan candidate carries a placeholder location for display only.
    """
    return EntryRecord(
        entry=None,
        artist=line.artist,
        title=line.title,
        audio_id="",
        filesize="",
        playtime_float="",
        bitrate="",
        album="",
        file_name="",
        location=LocationParts(volume="", volumeid="", dir_value="", file_name=""),
        # no filesystem file backs a tracklist candidate
        source_path=None,
    )


@dataclass(frozen=True)
class Candidate:
    """One input entry in input order. record None marks an entry that
    could not be parsed; the report still needs its line_number and
    raw_text, which is why unparseable entries travel in the same list
    rather than beside it (DL-274). artist and title are what the report
    shows."""

    line_number: int
    raw_text: str
    artist: str
    title: str
    record: Optional[EntryRecord]


def text_candidates(text: str) -> list[Candidate]:
    """parse_tracklist's parsed and unparseable lines as one Candidate
    list in line order. line_number is the physical 1-based line, the
    same number parse_tracklist assigns, so the text path's report is
    unchanged by the seam (DL-279)."""
    parsed, unparseable = parse_tracklist(text)
    candidates = [
        Candidate(line.line_number, line.raw_text, line.artist, line.title, tracklist_record(line))
        for line in parsed
    ]
    candidates.extend(
        Candidate(line.line_number, line.raw_text, "", "", None) for line in unparseable
    )
    # One list in physical line order, the order the report rows of the
    # recorded text corpus hold (DL-279).
    candidates.sort(key=lambda candidate: candidate.line_number)
    return candidates


@dataclass(frozen=True)
class TracklistResolution:
    line: ParsedLine
    outcome: str  # "matched", "unmatched", "ambiguous"
    matched_record: Optional[EntryRecord] = None


@dataclass(frozen=True)
class CandidateResolution:
    """One Candidate's outcome. matched_record is the collection record
    it resolved to, set only when outcome is 'matched'. 'unparseable' is
    the outcome of a record-None Candidate, which never reaches
    match_records (DL-274)."""

    candidate: Candidate
    outcome: str  # "matched", "unmatched", "ambiguous", "unparseable"
    matched_record: Optional[EntryRecord] = None


def resolve_candidates(
    candidates: list[Candidate], collection: list[EntryRecord]
) -> list[CandidateResolution]:
    """Resolve every candidate against collection, in input order.

    The candidate index is built once with build_new_indexes over
    collection at MatchConfidence.LOOSE, then match_records is called once
    per candidate with old_records holding that single record and the
    shared index passed as indexes; the returned stats dict distinguishes
    matched, unmatched and ambiguous for that one record. A candidate
    whose record is None is 'unparseable' and never reaches match_records.
    match_records' returned mapping is keyed by old_record.primary_key -
    on a matched outcome the matched record is read back via
    record.primary_key (not a hardcoded ""), so the lookup stays correct
    even if LocationParts.primary_key's concatenation formula ever changes.
    """
    # index built once over the full collection; reused by every
    # per-candidate match_records call below so the O(collection) cost
    # stays at one (DL-025)
    # LOOSE with the candidate as the old side and the collection as the
    # new: the cascade tries tiers strongest first, so a candidate carrying
    # more than artist and title reaches the stricter tiers at this level
    # (DL-276), and refutation's verdicts are symmetric in which side is
    # disk (DL-278).
    indexes = build_new_indexes(collection, MatchConfidence.LOOSE)
    resolutions: list[CandidateResolution] = []
    for candidate in candidates:
        record = candidate.record
        if record is None:
            resolutions.append(CandidateResolution(candidate=candidate, outcome="unparseable"))
            continue
        # One record per call: ambiguity is counted per old record (DL-278).
        mapping, stats, _samples = match_records(
            [record], collection, MatchConfidence.LOOSE, indexes=indexes
        )
        if stats["matched"] == 1:
            resolutions.append(
                CandidateResolution(
                    candidate=candidate, outcome="matched", matched_record=mapping.get(record.primary_key)
                )
            )
        elif stats["ambiguous"] == 1:
            resolutions.append(CandidateResolution(candidate=candidate, outcome="ambiguous"))
        else:
            resolutions.append(CandidateResolution(candidate=candidate, outcome="unmatched"))
    return resolutions


def resolve_tracklist(
    lines: list[ParsedLine], collection: list[EntryRecord]
) -> list[TracklistResolution]:
    """Resolve parsed lines through resolve_candidates, one
    TracklistResolution per line in input order. Kept for callers that
    hold ParsedLine values rather than Candidates."""
    candidates = [
        Candidate(line.line_number, line.raw_text, line.artist, line.title, tracklist_record(line))
        for line in lines
    ]
    return [
        TracklistResolution(line=line, outcome=resolution.outcome, matched_record=resolution.matched_record)
        for line, resolution in zip(lines, resolve_candidates(candidates, collection))
    ]
