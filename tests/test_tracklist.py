"""Tracklist: plain-text 'Artist - Title' parsing and per-line collection resolution."""

from __future__ import annotations

from unittest.mock import patch

from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.tracklist import (
    Candidate,
    parse_tracklist,
    resolve_candidates,
    resolve_tracklist,
    text_candidates,
)


def _collection_record(artist: str, title: str, filename: str = "track.mp3") -> EntryRecord:
    return EntryRecord(
        entry=None,
        artist=artist,
        title=title,
        audio_id="",
        filesize="",
        playtime_float="",
        bitrate="",
        album="",
        file_name=filename,
        location=LocationParts(volume="C:", volumeid="C:", dir_value="/:Music/:", file_name=filename),
    )


def test_three_lines_parse_to_three_records() -> None:
    text = "Artist One - Title One\nArtist Two - Title Two\nArtist Three - Title Three\n"
    parsed, unparseable = parse_tracklist(text)
    assert unparseable == []
    assert [(p.artist, p.title) for p in parsed] == [
        ("Artist One", "Title One"),
        ("Artist Two", "Title Two"),
        ("Artist Three", "Title Three"),
    ]


def test_blank_and_comment_lines_are_skipped() -> None:
    text = "Artist - Title\n\n# a comment\nArtist Two - Title Two\n"
    parsed, unparseable = parse_tracklist(text)
    assert unparseable == []
    assert len(parsed) == 2


def test_bare_title_with_no_delimiter_is_unparseable() -> None:
    text = "Just A Title With No Delimiter\n"
    parsed, unparseable = parse_tracklist(text)
    assert parsed == []
    assert len(unparseable) == 1
    assert unparseable[0].line_number == 1


def test_hyphen_without_surrounding_spaces_survives_inside_title() -> None:
    text = "Artist - Re-Edit Title\n"
    parsed, _ = parse_tracklist(text)
    assert parsed[0].artist == "Artist"
    assert parsed[0].title == "Re-Edit Title"


def test_whitespace_around_each_half_is_stripped() -> None:
    text = "  Artist   -   Title  \n"
    parsed, _ = parse_tracklist(text)
    assert parsed[0].artist == "Artist"
    assert parsed[0].title == "Title"


def test_empty_half_is_unparseable() -> None:
    text = " - Title\n"
    parsed, unparseable = parse_tracklist(text)
    assert parsed == []
    assert len(unparseable) == 1


def test_leading_track_number_prefix_is_stripped() -> None:
    text = "1 - Artist Name - Track Title\n"
    parsed, unparseable = parse_tracklist(text)
    assert unparseable == []
    assert parsed[0].artist == "Artist Name"
    assert parsed[0].title == "Track Title"


def test_artist_starting_with_a_digit_is_not_treated_as_a_track_number() -> None:
    text = "2Pac - California Love\n"
    parsed, unparseable = parse_tracklist(text)
    assert unparseable == []
    assert parsed[0].artist == "2Pac"
    assert parsed[0].title == "California Love"


# exercises the per-line match_records call (DL-025): two identical lines
# must resolve independently rather than collapsing onto one shared result
def test_two_identical_lines_resolve_independently() -> None:
    text = "Artist - Title\nArtist - Title\n"
    parsed, _ = parse_tracklist(text)
    collection = [_collection_record("Artist", "Title")]
    resolutions = resolve_tracklist(parsed, collection)
    assert len(resolutions) == 2
    assert all(r.outcome == "matched" for r in resolutions)


def test_no_delimiter_line_lands_in_unparseable_with_line_number() -> None:
    text = "Artist - Title\nNoDelimiterHere\n"
    parsed, unparseable = parse_tracklist(text)
    assert len(parsed) == 1
    assert len(unparseable) == 1
    assert unparseable[0].line_number == 2


def test_line_matching_two_collection_entries_is_ambiguous() -> None:
    text = "Artist - Title\n"
    parsed, _ = parse_tracklist(text)
    collection = [
        _collection_record("Artist", "Title", "one.mp3"),
        _collection_record("Artist", "Title", "two.mp3"),
    ]
    resolutions = resolve_tracklist(parsed, collection)
    assert resolutions[0].outcome == "ambiguous"


def test_line_matching_nothing_is_unmatched() -> None:
    text = "Artist - Title\n"
    parsed, _ = parse_tracklist(text)
    resolutions = resolve_tracklist(parsed, [])
    assert resolutions[0].outcome == "unmatched"


def test_resolution_order_matches_input_order_with_middle_line_unmatched() -> None:
    text = "Artist A - Title A\nArtist B - Title B\nArtist C - Title C\n"
    parsed, _ = parse_tracklist(text)
    collection = [_collection_record("Artist A", "Title A"), _collection_record("Artist C", "Title C")]
    resolutions = resolve_tracklist(parsed, collection)
    assert [r.outcome for r in resolutions] == ["matched", "unmatched", "matched"]
    assert resolutions[0].line.artist == "Artist A"
    assert resolutions[2].line.artist == "Artist C"


def test_matched_resolution_carries_the_collection_records_primary_key() -> None:
    text = "Artist - Title\n"
    parsed, _ = parse_tracklist(text)
    collection = [_collection_record("Artist", "Title", "track.mp3")]
    resolutions = resolve_tracklist(parsed, collection)
    assert resolutions[0].matched_record.primary_key == collection[0].primary_key


def test_text_candidates_order() -> None:
    """Parsed and unparseable lines come back as one list in physical
    line order, each numbered as parse_tracklist numbers it, with a None
    record exactly on the unparseable lines.

    Mutation: text_candidates drops its
        candidates.sort(key=line_number), so the unparseable lines
        follow every parsed line and line_number reads [1, 4, 2, 5].
    Observed:
        E   assert [1, 4, 2, 5] == [1, 2, 4, 5]
        E     
        E     At index 1 diff: 4 != 2
        E     Use -v to get more diff
    """
    text = "A - One\nno delimiter\n# comment\nB - Two\nalso bad\n"
    candidates = text_candidates(text)
    assert [c.line_number for c in candidates] == [1, 2, 4, 5]
    assert [c.record is None for c in candidates] == [False, True, False, True]
    assert candidates[1].raw_text == "no delimiter"
    assert (candidates[2].artist, candidates[2].title) == ("B", "Two")


def test_resolve_candidates_unparseable() -> None:
    """A record-None Candidate resolves as 'unparseable' without
    match_records ever being called for it, and a parsed candidate
    beside it still resolves.

    Mutation: resolve_candidates calls match_records([record], ...)
        before its `record is None` check, so the patched match_records
        raises for the unparseable candidate.
    Observed:
        E   AssertionError: match_records called for an unparseable candidate
    """
    unparseable = Candidate(3, "no delimiter", "", "", None)

    def _refuse(*_args, **_kwargs):
        raise AssertionError("match_records called for an unparseable candidate")

    with patch("traktor_nml.tracklist.match_records", _refuse):
        resolutions = resolve_candidates([unparseable], [_collection_record("A", "One")])
    assert [(r.candidate, r.outcome, r.matched_record) for r in resolutions] == [
        (unparseable, "unparseable", None)
    ]

    parsed = text_candidates("A - One\n")[0]
    collection = [_collection_record("A", "One")]
    mixed = resolve_candidates([parsed, unparseable], collection)
    assert [r.outcome for r in mixed] == ["matched", "unparseable"]
    assert mixed[0].matched_record.primary_key == collection[0].primary_key
