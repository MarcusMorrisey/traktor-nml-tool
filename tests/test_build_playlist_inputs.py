"""build-playlist over file-derived inputs, resolved through the real
cascade against a collection built to sit where the input files sit."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

from traktor_nml.buildplaylist import assemble_output
from traktor_nml.model import EntryRecord, LocationParts, collection_records, encode_traktor_dir
from traktor_nml.playlistinput import InputFormat, read_csv, read_folder, read_m3u
from traktor_nml.tracklist import Candidate, resolve_candidates
from traktor_nml.xmlio import parse_xml_bytes

_FIXED_UUID = uuid.UUID("00000000-0000-4000-8000-000000000000")


def _entry_for(path: Path, artist: str = "", title: str = "", time: str = "", size_kb: str = "") -> str:
    resolved = path.resolve()
    dir_value = encode_traktor_dir("/".join(resolved.parent.parts[1:]))
    drive = resolved.drive or "C:"
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="{dir_value}" FILE="{resolved.name}" VOLUME="{drive}" VOLUMEID="{drive}"></LOCATION>'
        f'<INFO BITRATE="320" PLAYTIME_FLOAT="{time}" FILESIZE="{size_kb}"></INFO>'
        "</ENTRY>"
    )


def _nml(entries: list[str]) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{len(entries)}">{"".join(entries)}</COLLECTION>'
        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0">'
        "</SUBNODES></NODE></PLAYLISTS><SETS></SETS><INDEXING></INDEXING></NML>"
    )


def test_folder_input_writes_playlist_in_folder_order(tmp_path: Path) -> None:
    """Files sitting at their collection locations resolve, and the
    playlist lists them in the folder's numeric-aware order.

    Mutation: read_folder sorts children with key=lambda child:
        child.name, so the playlist's primary keys read '1 - a.mp3', '10
        - c.mp3', '2 - b.mp3'.
    Observed:
        E   AssertionError: assert ['1 - a.mp3',..., '2 - b.mp3'] == ['1 - a.mp3',... '10 - c.mp3']
        E     At index 1 diff: '10 - c.mp3' != '2 - b.mp3'
    """
    music = tmp_path / "Music" / "Techno" / "Set"
    music.mkdir(parents=True)
    names = ["10 - c.mp3", "2 - b.mp3", "1 - a.mp3"]
    for name in names:
        (music / name).write_bytes(b"\0" * 4096)
    source = _nml([_entry_for(music / name, size_kb="4") for name in names])
    root = parse_xml_bytes(source.encode("utf-8"))
    with patch("uuid.uuid4", return_value=_FIXED_UUID):
        result = assemble_output(source, root, read_folder(music).candidates, "Set")
    assert result.errors == []
    keys = [line.split('KEY="')[1].split('"')[0] for line in result.output.split("<PRIMARYKEY")[1:]]
    assert [key.rsplit("/:", 1)[1] for key in keys] == ["1 - a.mp3", "2 - b.mp3", "10 - c.mp3"]


def test_folder_file_not_in_collection_is_unmatched(tmp_path: Path) -> None:
    """A file the collection does not hold is an unmatched row, and no
    ENTRY is added for it.

    Mutation: _resolve_lines appends an UnresolvedRow only when
        resolution.outcome is not 'unmatched', so stray.mp3 is missing
        from unresolved_rows.
    Observed:
        E   AssertionError: assert [] == [('stray.mp3', 'unmatched')]
        E     Right contains one more item: ('stray.mp3', 'unmatched')
    """
    (tmp_path / "stray.mp3").write_bytes(b"\0" * 4096)
    source = _nml([])
    root = parse_xml_bytes(source.encode("utf-8"))
    result = assemble_output(source, root, read_folder(tmp_path).candidates, "Set", allow_unmatched=True)
    assert [(row.raw_text, row.kind) for row in result.unresolved_rows] == [("stray.mp3", "unmatched")]
    assert result.errors == ["no_entries_resolved"]


def test_two_location_collection_resolves_to_the_folders_copy(tmp_path: Path) -> None:
    """A collection holding the same file name, artist, title and size
    at two locations resolves the folder's file uniquely at
    path_suffix_3, with no exact-location pre-pass.

    Mutation: diskscan._placeholder_location returns a location with an
        empty dir_value, so path_suffix_3 cannot fire and the candidate
        resolves to neither copy.
    Observed:
        E   AssertionError: assert 'unmatched' == 'matched'
    """
    here = tmp_path / "Music" / "Techno" / "Artist"
    here.mkdir(parents=True)
    track = here / "track.mp3"
    track.write_bytes(b"\0" * 4096)
    elsewhere = tmp_path / "Backup" / "Old" / "Other" / "track.mp3"
    source = _nml([
        _entry_for(track, "A", "T", size_kb="4"),
        _entry_for(elsewhere, "A", "T", size_kb="4"),
    ])
    root = parse_xml_bytes(source.encode("utf-8"))
    candidate = read_folder(here).candidates[0]
    resolution = resolve_candidates([candidate], collection_records(root))[0]
    assert resolution.outcome == "matched"
    assert resolution.matched_record.location.file_name == "track.mp3"
    assert resolution.matched_record.location.decoded_dir.parts[-3:] == ("Music", "Techno", "Artist")


def _collection_record(time: str, size: str, dir_value: str = "/:Music/:") -> EntryRecord:
    return EntryRecord(
        entry=None, artist="A", title="T", audio_id="", filesize=size, playtime_float=time,
        bitrate="", album="", file_name="track.mp3",
        location=LocationParts("C:", "C:", dir_value, "track.mp3"),
    )


def test_disk_candidate_refuted_by_duration_kept_across_size(tmp_path: Path) -> None:
    """With the disk candidate on the old side, a collection entry whose
    duration is a factor off is refuted, and one whose size differs is
    kept, since size does not refute across sources.

    Mutation: matching._Claims sets from_disk = False, so both sides read
        as one source, the 11% size difference refutes, and the 9000 KB
        entry comes back unmatched. (Swapping match_records' sides was
        tried first and the test still passed: refutation is symmetric
        in direction, DL-278.)
    Observed:
        E   AssertionError: assert 'unmatched' == 'matched'
    """
    disk = EntryRecord(
        entry=None, artist="A", title="T", audio_id="", filesize="8000", playtime_float="200.000",
        bitrate="", album="", file_name="track.mp3",
        location=LocationParts("", "", "/:x/:", "track.mp3"), source_path=tmp_path / "track.mp3",
    )
    candidate = Candidate(1, "track.mp3", "A", "T", disk)
    assert resolve_candidates([candidate], [_collection_record("30.0", "8000")])[0].outcome == "unmatched"
    assert resolve_candidates([candidate], [_collection_record("200.0", "9000")])[0].outcome == "matched"


def test_m3u_mixing_present_and_absent_writes_both_entries(tmp_path: Path) -> None:
    """A playlist built from an M3U whose first path is a file on this
    machine and whose second exists only in the collection: both entries
    are written, the absent one matched from its path string.

    Mutation: read_m3u drops a path line whose file does not exist on
        this machine, so only present.mp3 is written and entries_written
        is 1.
    Observed:
        E       assert 1 == 2
    """
    music = tmp_path / "Music" / "Techno" / "Set"
    music.mkdir(parents=True)
    present = music / "present.mp3"
    present.write_bytes(b"\0" * 4096)
    absent = music / "absent.mp3"
    source = _nml([_entry_for(present, size_kb="4"), _entry_for(absent)])
    playlist = tmp_path / "set.m3u"
    playlist.write_text(f"{present}\n/Volumes/Mac/Music/Techno/Set/absent.mp3\n", encoding="utf-8")
    root = parse_xml_bytes(source.encode("utf-8"))
    with patch("uuid.uuid4", return_value=_FIXED_UUID):
        result = assemble_output(source, root, read_m3u(playlist).candidates, "Set")
    assert result.errors == []
    assert result.stats["entries_written"] == 2


def test_cli_build_playlist_over_m3u_mixing_present_and_absent(tmp_path: Path) -> None:
    r"""The CLI builds a playlist from an M3U whose first path is a file
    on this machine and whose second exists only in the collection:
    both entries are written, the absent one matched from its path
    string (DL-275).

    Mutation: read_m3u drops a path line whose file does not exist on
        this machine, so only present.mp3 is written and stdout holds
        entries_written=1.
    Observed:
        E       AssertionError: assert 'entries_written=2' in 'input_format=m3u\ninput_encoding=utf-8-sig\nlines_read=1\nlines_resolved=1\nunresolved_unparseable=0\nunresolved_unmatched=0\nunresolved_ambiguous=0\nplaylist_name=Set\nentries_written=1\noutput_written=out.nml\n'
        E        +  where 'input_format=m3u\ninput_encoding=utf-8-sig\nlines_read=1\nlines_resolved=1\nunresolved_unparseable=0\nunresolved_unmatched=0\nunresolved_ambiguous=0\nplaylist_name=Set\nentries_written=1\noutput_written=out.nml\n' = RunResult(exit_code=0, stdout='input_format=m3u\ninput_encoding=utf-8-sig\nlines_read=1\nlines_resolved=1\nunresolved_...solved_unmatched=0\nunresolved_ambiguous=0\nplaylist_name=Set\nentries_written=1\noutput_written=out.nml\n', stderr='').stdout
    """
    from tests.conftest import run_tool

    music = tmp_path / "Music" / "Techno" / "Set"
    music.mkdir(parents=True)
    present = music / "present.mp3"
    present.write_bytes(b"\0" * 4096)
    absent = music / "absent.mp3"
    (tmp_path / "base.nml").write_text(
        _nml([_entry_for(present, size_kb="4"), _entry_for(absent)]), encoding="utf-8", newline=""
    )
    (tmp_path / "set.m3u").write_text(f"{present}\n/Volumes/Mac/Music/Techno/Set/absent.mp3\n", encoding="utf-8")
    with patch("uuid.uuid4", return_value=_FIXED_UUID):
        result = run_tool(["build-playlist", "base.nml", "set.m3u", "out.nml", "--name", "Set"], cwd=tmp_path)
    assert result.exit_code == 0, result.stderr
    assert "entries_written=2" in result.stdout


def test_csv_input_reports_format_and_encoding_and_writes_playlist(tmp_path: Path) -> None:
    """A CSV read names format csv and codec utf-8-sig - the values a CSV
    run prints as input_format and input_encoding (DL-280) - and its row
    resolves and is written. Run below the CLI, so it guards the reader;
    test_cli_run_over_csv_prints_format_and_encoding_first guards the
    CLI's printing of the same values.

    Mutation: read_csv returns InputRead(InputFormat.TEXT, ...), so the
        read names format text.
    Observed:
        E       AssertionError: assert (<InputFormat..., 'utf-8-sig') == (<InputFormat..., 'utf-8-sig')
        E
        E         At index 0 diff: <InputFormat.TEXT: 'text'> != <InputFormat.CSV: 'csv'>
    """
    track = tmp_path / "Music" / "a.mp3"
    source = _nml([_entry_for(track, "A", "T")])
    listing = tmp_path / "list.csv"
    listing.write_text("Artist,Title\nA,T\n", encoding="utf-8")
    read = read_csv(listing)
    assert (read.format, read.encoding) == (InputFormat.CSV, "utf-8-sig")
    root = parse_xml_bytes(source.encode("utf-8"))
    with patch("uuid.uuid4", return_value=_FIXED_UUID):
        result = assemble_output(source, root, read.candidates, "L")
    assert result.errors == []
    assert result.stats["entries_written"] == 1


def test_cli_run_over_csv_prints_format_and_encoding_first(tmp_path: Path) -> None:
    """A CSV run prints input_format=csv and input_encoding before the
    stats keys (DL-294).

    Mutation: _handle_build_playlist prints input_format and
        input_encoding after the stats loop, so stdout's first line is
        lines_read=1.
    Observed:
        E       AssertionError: assert ['lines_read=...nparseable=0'] == ['input_forma...lines_read=1']
        E         
        E         At index 0 diff: 'lines_read=1' != 'input_format=csv'
        E         Use -v to get more diff
    """
    from tests.conftest import run_tool

    track = tmp_path / "Music" / "a.mp3"
    (tmp_path / "base.nml").write_text(_nml([_entry_for(track, "A", "T")]), encoding="utf-8", newline="")
    (tmp_path / "list.csv").write_text("Artist,Title\nA,T\n", encoding="utf-8")
    result = run_tool(["build-playlist", "base.nml", "list.csv", "out.nml", "--name", "L"], cwd=tmp_path)
    assert result.exit_code == 0, result.stderr
    assert result.stdout.splitlines()[:3] == ["input_format=csv", "input_encoding=utf-8-sig", "lines_read=1"]


def test_cli_prints_the_raw_codec_name_the_screen_relabels(tmp_path: Path) -> None:
    """The CLI's input_encoding= is InputRead.encoding as the reader
    returned it: a UTF-8 CSV with a byte-order mark prints utf-8-sig and a
    cp1252 CSV prints cp1252. The screen's UTF-8 and Windows-1252 are
    buildplaylist_view.encoding_label's and never reach stdout (DL-294,
    DL-303).

    Mutation: build_playlist_cmd.py printed
        f"input_encoding={encoding_label(input_read.encoding)}", importing
        encoding_label from traktor_nml.gui.buildplaylist_view, and this
        guard rerun.
    Observed:
        E       AssertionError: assert 'input_encoding=UTF-8' == 'input_encoding=utf-8-sig'
        E
        E         - input_encoding=utf-8-sig
        E         ?                ^^^  ----
        E         + input_encoding=UTF-8
        E         ?                ^^^
    """
    from tests.conftest import run_tool

    track = tmp_path / "Music" / "a.mp3"
    (tmp_path / "base.nml").write_text(_nml([_entry_for(track, "A", "T")]), encoding="utf-8", newline="")
    (tmp_path / "bom.csv").write_bytes(b"\xef\xbb\xbfArtist,Title\r\nA,T\r\n")
    (tmp_path / "win.csv").write_bytes("Artist,Title\r\nA,T\r\nBeyonc\u00e9,Halo\r\n".encode("cp1252"))
    bom = run_tool(["build-playlist", "base.nml", "bom.csv", "a.nml", "--name", "L"], cwd=tmp_path)
    win = run_tool(
        ["build-playlist", "base.nml", "win.csv", "b.nml", "--name", "L", "--allow-unmatched"], cwd=tmp_path
    )
    assert bom.stdout.splitlines()[1] == "input_encoding=utf-8-sig"
    assert win.stdout.splitlines()[1] == "input_encoding=cp1252"


def test_cli_unresolved_label_is_position_for_folder_and_line_otherwise(tmp_path: Path) -> None:
    r"""A folder run labels an unresolved row position=, because its
    line_number is the file's place in name order; a CSV run keeps line=
    (DL-300).

    Mutation: _write_unresolved_report sets label = "line" for every
        format, so the folder run prints unresolved line=1.
    Observed:
        E       assert "unresolved position=1 kind=unmatched text='stray.mp3'" in "input_format=folder\ninput_encoding=n/a\nlines_read=1\nlines_resolved=0\nunresolved_unparseable=0\nunresolved_unmatched=1\nunresolved_ambiguous=0\nplaylist_name=None\nentries_written=0\nunresolved line=1 kind=unmatched text='stray.mp3'\n"
        E        +  where "input_format=folder\ninput_encoding=n/a\nlines_read=1\nlines_resolved=0\nunresolved_unparseable=0\nunresolved_unmatched=1\nunresolved_ambiguous=0\nplaylist_name=None\nentries_written=0\nunresolved line=1 kind=unmatched text='stray.mp3'\n" = RunResult(exit_code=2, stdout="input_format=folder\ninput_encoding=n/a\nlines_read=1\nlines_resolved=0\nunresolved_unp...n=0\nunresolved line=1 kind=unmatched text='stray.mp3'\n", stderr='no_entries_resolved\nbuild_playlist_aborted=true\n').stdout
    """
    from tests.conftest import run_tool

    folder = tmp_path / "set"
    folder.mkdir()
    (folder / "stray.mp3").write_bytes(b"\0" * 4096)
    (tmp_path / "base.nml").write_text(_nml([]), encoding="utf-8", newline="")
    folder_run = run_tool(
        ["build-playlist", "base.nml", "set", "out.nml", "--name", "Set", "--allow-unmatched", "--dry-run"],
        cwd=tmp_path,
    )
    assert "unresolved position=1 kind=unmatched text='stray.mp3'" in folder_run.stdout
    assert "unresolved line=" not in folder_run.stdout

    (tmp_path / "list.csv").write_text("Artist,Title\nA,T\n", encoding="utf-8")
    csv_run = run_tool(
        ["build-playlist", "base.nml", "list.csv", "out.nml", "--name", "Set", "--allow-unmatched", "--dry-run"],
        cwd=tmp_path,
    )
    assert "unresolved line=2 kind=unmatched" in csv_run.stdout
