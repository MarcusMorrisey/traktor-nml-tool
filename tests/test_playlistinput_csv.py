"""playlistinput's CSV reader and template. System interpreter, no nicegui."""

from __future__ import annotations

from pathlib import Path

import pytest

from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.playlistinput import (
    CSV_COLUMNS,
    InputFormat,
    InputReadError,
    csv_template_bytes,
    parse_duration,
    read_csv,
)
from traktor_nml.tracklist import resolve_candidates


def _write(tmp_path: Path, text: str, encoding: str = "utf-8", name: str = "list.csv") -> Path:
    path = tmp_path / name
    path.write_bytes(text.encode(encoding))
    return path


def test_template_round_trips_to_zero_candidates(tmp_path: Path) -> None:
    """The template's own bytes, fed to read_csv, parse with no error to
    zero candidates, and its header is CSV_COLUMNS in order. The bytes go
    through the parser rather than being compared with a header string,
    which stays green when the parser and the template disagree (DL-189).

    Mutation: csv_template_bytes writes 'Track' in place of the Title
        column's header, so read_csv raises InputReadError
        csv_header_missing on the template.
    Observed:
        E       traktor_nml.playlistinput.InputReadError: csv_header_missing
    """
    path = tmp_path / "template.csv"
    path.write_bytes(csv_template_bytes())
    read = read_csv(path)
    assert read.candidates == []
    assert csv_template_bytes().startswith(b"\xef\xbb\xbf")
    assert csv_template_bytes().endswith(b"\r\n")
    assert csv_template_bytes().decode("utf-8-sig").strip() == ",".join(c.header for c in CSV_COLUMNS)


def test_headers_case_whitespace_and_unknown_columns(tmp_path: Path) -> None:
    """Headers match after strip and casefold, and an unknown column is
    ignored.

    Mutation: _header_index compares cell.strip() without casefold(), so
        'TITLE' matches no column and read_csv raises
        csv_header_missing.
    Observed:
        E       traktor_nml.playlistinput.InputReadError: csv_header_missing
    """
    path = _write(tmp_path, " artist ,Notes,TITLE\nA,ignore me,T\n")
    candidate = read_csv(path).candidates[0]
    assert (candidate.artist, candidate.title) == ("A", "T")


def test_missing_title_header_refuses(tmp_path: Path) -> None:
    """A header without Title refuses with csv_header_missing.

    Mutation: _choose_delimiter requires only the Artist column, so
        read_csv reads 'Artist,Album' as unparseable rows and raises
        nothing.
    Observed:
        E       Failed: DID NOT RAISE <class 'traktor_nml.playlistinput.InputReadError'>
    """
    with pytest.raises(InputReadError) as error:
        read_csv(_write(tmp_path, "Artist,Album\nA,B\n"))
    assert error.value.code == "csv_header_missing"


def test_semicolon_csv_parses_like_its_comma_twin(tmp_path: Path) -> None:
    """A semicolon file from a comma-decimal Excel reads identically to
    the comma file, commas inside a title included.

    Mutation: _choose_delimiter always returns ',', so the semicolon
        header is one unknown column and read_csv raises
        csv_header_missing.
    Observed:
        E       traktor_nml.playlistinput.InputReadError: csv_header_missing
    """
    comma = read_csv(_write(tmp_path, 'Artist,Title,Duration\nA,"One, Two",3:35\n', name="c.csv"))
    semi = read_csv(_write(tmp_path, "Artist;Title;Duration\nA;One, Two;3:35\n", name="s.csv"))
    assert [c.record for c in comma.candidates] == [c.record for c in semi.candidates]


@pytest.mark.parametrize(
    "text,expected",
    [("215", "215.000"), ("215.4", "215.400"), ("3:35", "215.000"), ("1:02:03", "3723.000"),
     ("", ""), ("abc", ""), ("3:xx", "")],
)
def test_duration_forms(text: str, expected: str) -> None:
    """Seconds, m:ss and h:mm:ss convert; empty and unreadable cells give
    ''.

    Mutation: parse_duration assigns hours, minutes = first, second for
        two-part values as well as three-part ones, so '3:35' converts
        to 10835.000 in place of 215.000.
    Observed:
        E       AssertionError: assert '10835.000' == '215.000'
        E
        E         - 215.000
        E         ? -
        E         + 10835.000
        E         ?  +++
    """
    assert parse_duration(text) == expected


def test_rows_empty_unparseable_and_line_numbers(tmp_path: Path) -> None:
    """An all-empty row is skipped, a row missing Title is unparseable,
    and line_number is the row's starting physical line even after a
    quoted multi-line cell.

    Mutation: read_csv numbers each row by its position in the reader,
        enumerate(reader, start=2), in place of the physical line it
        starts on, so the multi-line cell shifts the later line numbers.
    Observed:
        E       assert [2, 4, 5] == [2, 5, 6]
        E
        E         At index 1 diff: 4 != 5
    """
    text = 'Artist,Title\nA,"Line one\nline two"\n,\nB,\nC,Three\n'
    candidates = read_csv(_write(tmp_path, text)).candidates
    assert [c.line_number for c in candidates] == [2, 5, 6]
    assert [c.record is None for c in candidates] == [False, True, False]
    assert candidates[0].raw_text == 'A,"Line one\nline two"'


def test_cp1252_csv_reports_its_encoding(tmp_path: Path) -> None:
    """Bytes that are not UTF-8 decode as cp1252 and the read names that
    codec.

    Mutation: _decode_with_fallback decodes utf-8-sig with
        errors='replace', so the read reports 'utf-8-sig' in place of
        'cp1252'.
    Observed:
        E       AssertionError: assert 'utf-8-sig' == 'cp1252'
        E
        E         - cp1252
        E         + utf-8-sig
    """
    read = read_csv(_write(tmp_path, "Artist,Title\nBeyoncé,Halo\n", "cp1252"))
    assert read.format is InputFormat.CSV
    assert read.encoding == "cp1252"
    assert read.candidates[0].artist == "Beyoncé"


def _collection(file_name: str) -> EntryRecord:
    return EntryRecord(
        entry=None, artist="A", title="T", audio_id="", filesize="", playtime_float="",
        bitrate="", album="", file_name=file_name,
        location=LocationParts("C:", "C:", "/:Music/:", file_name),
    )


def test_file_name_column_resolves_where_artist_title_is_ambiguous(tmp_path: Path) -> None:
    """Two collection entries share artist and title; the File name
    column resolves the row at artist_title_file, where the same row
    without it is ambiguous.

    Mutation: read_csv builds the EntryRecord with file_name='', so the
        row with a File name column is ambiguous at artist_title like
        the row without it.
    Observed:
        E       AssertionError: assert 'ambiguous' == 'matched'
        E
        E         - matched
        E         + ambiguous
    """
    collection = [_collection("a.mp3"), _collection("b.mp3")]
    with_file = read_csv(_write(tmp_path, "Artist,Title,File name\nA,T,b.mp3\n", name="f.csv")).candidates
    without = read_csv(_write(tmp_path, "Artist,Title\nA,T\n", name="n.csv")).candidates
    matched = resolve_candidates(with_file, collection)[0]
    assert matched.outcome == "matched"
    assert matched.matched_record.file_name == "b.mp3"
    assert resolve_candidates(without, collection)[0].outcome == "ambiguous"
