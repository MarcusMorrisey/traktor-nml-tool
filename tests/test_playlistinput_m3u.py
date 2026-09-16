"""playlistinput's M3U reader: #EXTINF attachment, path flavours, URL
lines, encodings, and the duration edge the matching tolerance sets.
System interpreter, no nicegui."""

from __future__ import annotations

from pathlib import Path

import pytest

from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.playlistinput import InputFormat, InputReadError, _path_string_record, read_m3u
from traktor_nml.tracklist import resolve_candidates


def _write(path: Path, text: str, encoding: str = "utf-8") -> Path:
    path.write_bytes(text.encode(encoding))
    return path


def test_extinf_attaches_to_next_path_line(tmp_path: Path) -> None:
    """Duration and 'Artist - Title' fill the next path line's record;
    a directive does not carry past its path line; -1 gives no duration;
    display text with no ' - ' leaves artist and title empty.

    The bare path directly follows a populated directive's path line, so
    a directive carried forward shows as filled fields rather than as
    empty ones indistinguishable from the correct result (DL-189).

    Mutation: read_m3u assigns extinf = pending without resetting
        pending to None, so /absent/Music/two.mp3 carries Alpha - One
        and 215.000.
    Observed:
        E       AssertionError: assert [('Alpha', 'O... ('', '', '')] == [('Alpha', 'O... ('', '', '')]
        E         At index 1 diff: ('Alpha', 'One', '215.000') != ('', '', '')
    """
    playlist = _write(tmp_path / "set.m3u8", (
        "#EXTM3U\n"
        "#EXTINF:215,Alpha - One\n"
        "/absent/Music/Alpha/one.mp3\n"
        "/absent/Music/two.mp3\n"
        "#EXTINF:-1,Just a name\n"
        "/absent/Music/three.mp3\n"
    ))
    read = read_m3u(playlist)
    records = [c.record for c in read.candidates]
    assert [(r.artist, r.title, r.playtime_float) for r in records] == [
        ("Alpha", "One", "215.000"), ("", "", ""), ("", "", ""),
    ]
    assert [c.line_number for c in read.candidates] == [3, 4, 6]


def test_path_lines_relative_windows_posix_and_url(tmp_path: Path) -> None:
    """A relative path present beside the playlist is indexed from disk;
    an absent Windows path and an absent POSIX path become path-string
    records; a URL line is unparseable.

    Mutation: read_m3u skips its _URL check, so the https:// line
        becomes a path-string record in place of None.
    Observed:
        E       AssertionError: assert EntryRecord(entry=None, artist='', title='', audio_id='', filesize='', playtime_float='', bitrate='', album='', file_n...n=LocationParts(volume='', volumeid='', dir_value='/:https:/:example.com/:', file_name='stream.mp3'), source_path=None) is None
    """
    (tmp_path / "Local").mkdir()
    (tmp_path / "Local" / "here.mp3").write_bytes(b"\0" * 2048)
    playlist = _write(tmp_path / "set.m3u8", (
        "Local/here.mp3\n"
        "Z:\\Music\\Techno\\gone.mp3\n"
        "/Users/x/Music/Techno/gone.mp3\n"
        "https://example.com/stream.mp3\n"
    ))
    candidates = read_m3u(playlist).candidates
    assert candidates[0].record.source_path is not None
    assert candidates[0].record.filesize == "2"
    assert candidates[1].record.source_path is None
    assert candidates[2].record.source_path is None
    assert candidates[3].record is None


def test_windows_and_posix_path_strings_decode_alike() -> None:
    """The same folders written as a Windows path and as a POSIX path
    give the same folder parts.

    Mutation: _path_flavour always returns PurePosixPath, so the Windows
        path string is one backslashed name with no folders and its
        dir_value reads '/:/:'.
    Observed:
        E       AssertionError: assert '/:/:' == '/:Sync/:Musi...hno/:Artist/:'
        E         - /:Sync/:Music/:Techno/:Artist/:
        E         + /:/:
    """
    windows = _path_string_record("D:\\Sync\\Music\\Techno\\Artist\\track.mp3", None)
    posix = _path_string_record("/Sync/Music/Techno/Artist/track.mp3", None)
    assert windows.location.dir_value == posix.location.dir_value == "/:Sync/:Music/:Techno/:Artist/:"
    assert windows.file_name == posix.file_name == "track.mp3"


def _collection(dir_value: str, time: str = "215.9") -> EntryRecord:
    return EntryRecord(
        entry=None, artist="Alpha", title="One", audio_id="", filesize="8000", playtime_float=time,
        bitrate="", album="", file_name="track.mp3",
        location=LocationParts("D:", "D:", dir_value, "track.mp3"),
    )


def test_mac_path_absent_here_matches_by_path_suffix_3(tmp_path: Path) -> None:
    """A Mac path that does not exist on this machine matches the
    collection entry under D:/Sync/Music/Techno/Artist through its last
    three folders, while a decoy with the same file name elsewhere does
    not make it ambiguous.

    Mutation: _path_string_record sets the location's dir_value to '',
        so path_suffix_3 cannot fire and the candidate resolves to
        neither entry.
    Observed:
        E       AssertionError: assert 'unmatched' == 'matched'
    """
    playlist = _write(tmp_path / "mac.m3u8", "/Users/x/Music/Techno/Artist/track.mp3\n")
    candidate = read_m3u(playlist).candidates[0]
    target = _collection("/:Sync/:Music/:Techno/:Artist/:")
    decoy = _collection("/:Sync/:Other/:Place/:Else/:")
    resolution = resolve_candidates([candidate], [target, decoy])[0]
    assert resolution.outcome == "matched"
    assert resolution.matched_record is target


def test_extinf_truncation_matched_and_gap_refuted(tmp_path: Path) -> None:
    """#EXTINF's integer seconds 0.9s under the collection's duration
    still match; a 5s gap is refuted.

    Mutation: _parse_extinf returns seconds='' for every directive, so
        the 220.0s collection entry is not refuted by duration and the
        second outcome is 'matched'.
    Observed:
        E       AssertionError: assert 'matched' == 'unmatched'
    """
    playlist = _write(tmp_path / "t.m3u8", "#EXTINF:215,Alpha - One\n/nowhere/a/b/c/track.mp3\n")
    candidate = read_m3u(playlist).candidates[0]
    assert resolve_candidates([candidate], [_collection("/:x/:", "215.9")])[0].outcome == "matched"
    assert resolve_candidates([candidate], [_collection("/:x/:", "220.0")])[0].outcome == "unmatched"


def test_extinf_whole_second_rounding_either_way_matches(tmp_path: Path) -> None:
    """A 421.53s collection PLAYTIME_FLOAT against #EXTINF 421 (truncated)
    and 422 (rounded): both whole-second forms match.

    Mutation: _parse_extinf formats seconds - 1, so #EXTINF 421 reads
        420.000, 1.53s under the collection, and is refuted.
    Observed:
        E       AssertionError: assert ['unmatched', 'matched'] == ['matched', 'matched']
        E         At index 0 diff: 'unmatched' != 'matched'
    """
    outcomes = []
    for seconds in ("421", "422"):
        playlist = _write(tmp_path / f"{seconds}.m3u8", f"#EXTINF:{seconds},Alpha - One\n/nowhere/a/b/c/track.mp3\n")
        candidate = read_m3u(playlist).candidates[0]
        outcomes.append(resolve_candidates([candidate], [_collection("/:x/:", "421.53")])[0].outcome)
    assert outcomes == ["matched", "matched"]


def test_encodings(tmp_path: Path) -> None:
    """A cp1252 .m3u reads and reports cp1252; the same bytes as .m3u8
    refuse with tracklist_decode_error.

    Mutation: read_m3u decodes a .m3u8 through _decode_with_fallback, so
        the cp1252 .m3u8 reads without raising InputReadError.
    Observed:
        E       Failed: DID NOT RAISE <class 'traktor_nml.playlistinput.InputReadError'>
    """
    body = "#EXTINF:100,Beyonc\u00e9 - Halo\n/nowhere/halo.mp3\n"
    m3u = _write(tmp_path / "set.m3u", body, "cp1252")
    read = read_m3u(m3u)
    assert read.format is InputFormat.M3U
    assert read.encoding == "cp1252"
    assert read.candidates[0].record.artist == "Beyonc\u00e9"

    m3u8 = _write(tmp_path / "set.m3u8", body, "cp1252")
    with pytest.raises(InputReadError) as error:
        read_m3u(m3u8)
    assert error.value.code == f"tracklist_decode_error={m3u8.as_posix()}"


def test_present_file_ignores_extinf(tmp_path: Path) -> None:
    """A file present on disk takes artist, title and duration from the
    file, not from its #EXTINF.

    Mutation: read_m3u fills a present file's empty artist, title and
        playtime_float from its #EXTINF, so the record reads ('Wrong',
        'Name', '300.000').
    Observed:
        E       AssertionError: assert ('Wrong', 'Name', '300.000') == ('', '', '')
        E         At index 0 diff: 'Wrong' != ''
    """
    (tmp_path / "real.mp3").write_bytes(b"\0" * 1024)
    playlist = _write(tmp_path / "s.m3u8", "#EXTINF:300,Wrong - Name\nreal.mp3\n")
    record = read_m3u(playlist).candidates[0].record
    assert (record.artist, record.title, record.playtime_float) == ("", "", "")
