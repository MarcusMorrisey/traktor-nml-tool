"""playlistinput: format detection and the plain-text reader.

Runs on the system interpreter with no nicegui installed (DL-069).
Each guard names the mutation it was proven against and quotes the
output that mutation produced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from traktor_nml.playlistinput import InputFormat, InputReadError, detect_format, read_input
from traktor_nml.tracklist import text_candidates


@pytest.mark.parametrize(
    "name,expected",
    [
        ("list.csv", InputFormat.CSV),
        ("LIST.CSV", InputFormat.CSV),
        ("set.m3u", InputFormat.M3U),
        ("set.m3u8", InputFormat.M3U),
        ("tracks.txt", InputFormat.TEXT),
        ("tracks", InputFormat.TEXT),
        ("tracks.nml", InputFormat.TEXT),
    ],
)
def test_detect_format(tmp_path: Path, name: str, expected: InputFormat) -> None:
    """Suffix decides a file's format, case-insensitively, and any
    suffix other than .csv, .m3u or .m3u8 - or none - is text (DL-281).

    Mutation: detect_format compares path.suffix without casefold(), so
        LIST.CSV detects as InputFormat.TEXT.
    Observed:
        E   AssertionError: assert <InputFormat.TEXT: 'text'> is <InputFormat.CSV: 'csv'>
        E    +  where <InputFormat.TEXT: 'text'> = detect_format(WindowsPath('C:/Users/marcu/AppData/Local/Temp/pytest-of-marcu/pytest-1318/test_detect_format_LIST_CSV_In1/LIST.CSV'))
    """
    path = tmp_path / name
    path.write_bytes(b"")
    assert detect_format(path) is expected


def test_detect_format_directory(tmp_path: Path) -> None:
    """A directory is a folder input whatever its name looks like: the
    is_dir check decides before any suffix is read (DL-281).

    Mutation: detect_format tests the suffix before path.is_dir(), so
        the folder named looks.csv detects as InputFormat.CSV.
    Observed:
        E   AssertionError: assert <InputFormat.CSV: 'csv'> is <InputFormat.FOLDER: 'folder'>
        E    +  where <InputFormat.CSV: 'csv'> = detect_format(WindowsPath('C:/Users/marcu/AppData/Local/Temp/pytest-of-marcu/pytest-1319/test_detect_format_directory0/looks.csv'))
        E    +  and   <InputFormat.FOLDER: 'folder'> = InputFormat.FOLDER
    """
    folder = tmp_path / "looks.csv"
    folder.mkdir()
    assert detect_format(folder) is InputFormat.FOLDER


def test_read_input_text(tmp_path: Path) -> None:
    r"""A text file reads as format text, codec utf-8-sig, with exactly
    the candidates text_candidates gives for its decoded text - a BOM
    stripped, not left on the first artist.

    Mutation: _decode_strict decodes with 'utf-8' in place of
        'utf-8-sig', so the BOM stays on the first artist and the
        candidates differ from text_candidates('A - One\nbad\n').
    Observed:
        E   AssertionError: assert [Candidate(li... record=None)] == [Candidate(li... record=None)]
        E     
        E     At index 0 diff: Candidate(line_number=1, raw_text='\ufeffA - One', artist='\ufeffA', title='One', record=EntryRecord(entry=None, artist='\ufeffA', title='One', audio_id='', filesize='', playtime_float='', bitrate='', album='', file_name='', location=LocationParts(volume='', volumeid='', dir_value='', file_name=''), source_path=None)) != Candidate(line_number=1, raw_text='A - One', artist='A', title='One', record=EntryRecord(entry=None, artist='A', title='One', audio_id='', filesize='', playtime_float='', bitrate='', album='', file_name='', location=LocationParts(volume...
        E     
        E     ...Full output truncated (2 lines hidden), use '-vv' to show
    """
    path = tmp_path / "tracks.txt"
    path.write_bytes(b"\xef\xbb\xbfA - One\nbad\n")
    read = read_input(path)
    assert read.format is InputFormat.TEXT
    assert read.encoding == "utf-8-sig"
    assert read.candidates == text_candidates("A - One\nbad\n")
    assert read.candidates[0].artist == "A"


def test_read_input_text_refusals(tmp_path: Path) -> None:
    """A missing path refuses with input_not_found and bytes that are
    not UTF-8 with tracklist_decode_error, each naming the posix path -
    the codes the CLI prints.

    Mutation: _decode_strict decodes with errors='replace', so the
        non-UTF-8 file reads without raising InputReadError.
    Observed:
        E   Failed: DID NOT RAISE <class 'traktor_nml.playlistinput.InputReadError'>
    """
    missing = tmp_path / "absent.txt"
    with pytest.raises(InputReadError) as missing_error:
        read_input(missing)
    assert missing_error.value.code == f"input_not_found={missing.as_posix()}"

    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"A - One\n\xff\xfe\n")
    with pytest.raises(InputReadError) as decode_error:
        read_input(bad)
    assert decode_error.value.code == f"tracklist_decode_error={bad.as_posix()}"


def test_read_input_dispatch_and_override(tmp_path: Path) -> None:
    """A .csv read with fmt text is parsed as text; each detected format
    reaches its own reader; a format that contradicts the path refuses
    with input_format_mismatch (DL-292, DL-294).

    Mutation: read_input ignores fmt and always calls detect_format, so
        read_input(csv_file, InputFormat.TEXT) returns format
        InputFormat.CSV.
    Observed:
        E       AssertionError: assert <InputFormat.CSV: 'csv'> is <InputFormat.TEXT: 'text'>
        E        +  where <InputFormat.CSV: 'csv'> = InputRead(format=<InputFormat.CSV: 'csv'>, encoding='utf-8-sig', candidates=[Candidate(line_number=2, raw_text='A - One', artist='A - One', title='', record=None)]).format
        E        +  and   <InputFormat.TEXT: 'text'> = InputFormat.TEXT
    """
    csv_file = tmp_path / "list.csv"
    csv_file.write_text("Artist,Title\nA - One\n", encoding="utf-8")
    as_text = read_input(csv_file, InputFormat.TEXT)
    assert as_text.format is InputFormat.TEXT
    assert [c.artist for c in as_text.candidates if c.record is not None] == ["A"]
    assert read_input(csv_file).format is InputFormat.CSV
    assert read_input(tmp_path).format is InputFormat.FOLDER

    with pytest.raises(InputReadError) as folder_on_file:
        read_input(csv_file, InputFormat.FOLDER)
    assert folder_on_file.value.code == "input_format_mismatch=folder"
    with pytest.raises(InputReadError) as csv_on_dir:
        read_input(tmp_path, InputFormat.CSV)
    assert csv_on_dir.value.code == "input_format_mismatch=csv"
