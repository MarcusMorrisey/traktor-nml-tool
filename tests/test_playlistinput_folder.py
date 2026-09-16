"""playlistinput's folder reader: its own files only, in numeric-aware
name order, indexed from disk. System interpreter, no nicegui."""

from __future__ import annotations

from pathlib import Path

import pytest

from traktor_nml.playlistinput import InputFormat, InputReadError, folder_order_key, read_folder


def _touch(path: Path, size: int = 1024) -> Path:
    path.write_bytes(b"\0" * size)
    return path


def test_folder_order_is_numeric_aware(tmp_path: Path) -> None:
    """'1 - a', '2 - b', '10 - c' read in that order.

    Mutation: read_folder sorts children with key=lambda child:
        child.name, so '10 - c.mp3' reads before '2 - b.mp3'.
    Observed:
        E   AssertionError: assert ['1 - a.mp3',..., '2 - b.mp3'] == ['1 - a.mp3',... '10 - c.mp3']
        E     At index 1 diff: '10 - c.mp3' != '2 - b.mp3'
    """
    for name in ("10 - c.mp3", "2 - b.mp3", "1 - a.mp3"):
        _touch(tmp_path / name)
    read = read_folder(tmp_path)
    assert read.format is InputFormat.FOLDER
    assert read.encoding == "n/a"
    assert [c.raw_text for c in read.candidates] == ["1 - a.mp3", "2 - b.mp3", "10 - c.mp3"]
    assert [c.line_number for c in read.candidates] == [1, 2, 3]


def test_folder_order_key_case_and_ties() -> None:
    """Case does not split the order, and names equal after casefolding
    and integer comparison still order totally by the plain name.

    Mutation: folder_order_key splits name without casefold(), so 'B
        2.mp3' sorts before 'a 10.mp3'.
    Observed:
        E   AssertionError: assert ['01 x.mp3', ..., 'track.mp3'] == ['01 x.mp3', ..., 'track.mp3']
        E     At index 3 diff: 'B 2.mp3' != 'a 10.mp3'
    """
    names = ["B 2.mp3", "a 10.mp3", "A 2.mp3", "01 x.mp3", "1 x.mp3", "track.mp3"]
    assert sorted(names, key=folder_order_key) == [
        "01 x.mp3", "1 x.mp3", "A 2.mp3", "a 10.mp3", "B 2.mp3", "track.mp3",
    ]


def test_subdirectory_files_are_not_candidates(tmp_path: Path) -> None:
    """A file inside a subfolder is not read, and a non-audio file is
    skipped.

    Mutation: read_folder iterates path.rglob('*') in place of
        path.iterdir(), so sub/inner.mp3 becomes a candidate.
    Observed:
        E   AssertionError: assert ['inner.mp3', 'top.mp3'] == ['top.mp3']
        E     At index 0 diff: 'inner.mp3' != 'top.mp3'
        E     Left contains one more item: 'top.mp3'
    """
    _touch(tmp_path / "top.mp3")
    _touch(tmp_path / "cover.jpg")
    (tmp_path / "sub").mkdir()
    _touch(tmp_path / "sub" / "inner.mp3")
    assert [c.raw_text for c in read_folder(tmp_path).candidates] == ["top.mp3"]


def test_folder_candidates_carry_disk_fields(tmp_path: Path) -> None:
    """Each record carries size in KB, the file name and the folder's
    own name in its placeholder location - the fields the path and size
    tiers read.

    Mutation: _record_for_file sets filesize=str(file_stat.st_size), so
        the record holds '8192' in place of '8'.
    Observed:
        E   AssertionError: assert '8192' == '8'
    """
    _touch(tmp_path / "a.mp3", 8192)
    record = read_folder(tmp_path).candidates[0].record
    assert record.filesize == "8"
    assert record.file_name == "a.mp3"
    assert record.location.decoded_dir.name == tmp_path.resolve().name


def test_folder_stat_failure_refuses(tmp_path: Path, monkeypatch) -> None:
    """A file that cannot be indexed refuses the read with
    input_read_error naming it, never a shorter list.

    Mutation: _index_or_refuse returns [] on DiskReadError, so
        read_folder returns zero candidates without raising
        InputReadError.
    Observed:
        E   Failed: DID NOT RAISE <class 'traktor_nml.playlistinput.InputReadError'>
    """
    from traktor_nml import diskscan

    _touch(tmp_path / "a.mp3")

    def _fail(paths, cache=None):
        raise diskscan.DiskReadError(Path(tmp_path / "a.mp3"))

    monkeypatch.setattr("traktor_nml.playlistinput.index_files", _fail)
    with pytest.raises(InputReadError) as error:
        read_folder(tmp_path)
    assert error.value.code == f"input_read_error={(tmp_path / 'a.mp3').as_posix()}"
