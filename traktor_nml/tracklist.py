"""External track-list parsing and per-line collection resolution.

A plain-text track list holds one 'Artist - Title' line per line. Each
parsed line becomes a candidate EntryRecord (entry=None), the same shape
diskscan.py already uses for disk-scanned candidates, and is resolved
against a base collection through the shared matching cascade in
matching.py at MatchConfidence.LOOSE - the only tier reachable for
text-only input is artist_title, since every field the stricter tiers
require (filesize, playtime_float, file_name, album) is empty for a
parsed line. matching.py and confidence.py are imported and called here,
never edited or wrapped in a subclass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .confidence import MatchConfidence
from .matching import build_new_indexes, match_records
from .model import EntryRecord, LocationParts


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
    entirely. A retained line splits on its first ' - ' occurrence into
    artist (left, stripped) and title (right, stripped); a line with no
    such occurrence, or with an empty half after stripping, becomes an
    unparseable record carrying its 1-based line number and raw text
    instead of being discarded.
    """
    parsed: list[ParsedLine] = []
    unparseable: list[UnparseableLine] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # search the raw (unstripped) line so the found index still lines up
        # with raw_line when slicing artist/title below (DL-031)
        delimiter_idx = raw_line.find(" - ")
        if delimiter_idx < 0:
            unparseable.append(UnparseableLine(line_number=line_number, raw_text=raw_line))
            continue
        artist = raw_line[:delimiter_idx].strip()
        title = raw_line[delimiter_idx + len(" - "):].strip()
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
class TracklistResolution:
    line: ParsedLine
    outcome: str  # "matched", "unmatched", "ambiguous"
    matched_record: Optional[EntryRecord] = None


def resolve_tracklist(
    lines: list[ParsedLine], collection: list[EntryRecord]
) -> list[TracklistResolution]:
    """Resolve every parsed line against collection, in input order.

    The candidate index is built once with build_new_indexes over
    collection at MatchConfidence.LOOSE, then match_records is called once
    per line with old_records holding that single line and the shared
    index passed as indexes; the returned stats dict distinguishes matched,
    unmatched and ambiguous for that one line. match_records' returned
    mapping is keyed by old_record.primary_key, which is always the empty
    string for a text-only tracklist record since its LocationParts carries
    no volume, dir or file - on a matched outcome the matched record is
    read back as mapping.get(""), never by any line-derived key.
    """
    # index built once over the full collection; reused by every per-line
    # match_records call below so the O(collection) cost stays at one (DL-025)
    indexes = build_new_indexes(collection, MatchConfidence.LOOSE)
    resolutions: list[TracklistResolution] = []
    for line in lines:
        record = tracklist_record(line)
        mapping, stats, _samples = match_records(
            [record], collection, MatchConfidence.LOOSE, indexes=indexes
        )
        if stats["matched"] == 1:
            resolutions.append(
                TracklistResolution(line=line, outcome="matched", matched_record=mapping.get(""))
            )
        elif stats["ambiguous"] == 1:
            resolutions.append(TracklistResolution(line=line, outcome="ambiguous"))
        else:
            resolutions.append(TracklistResolution(line=line, outcome="unmatched"))
    return resolutions
