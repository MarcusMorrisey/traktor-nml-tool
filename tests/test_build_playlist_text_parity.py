"""Golden replay of the plain-text build-playlist path (DL-279).

Each case under tests/baselines/build_playlist_text/<case>/ holds what
the CLI printed, the exit code it returned and every byte it wrote for
one invocation over the base collection and track list this module
builds. The corpus was recorded from the code as it stood before the
Candidate seam (DL-274) existed; replaying it here is the proof that
the seam left the text path's stdout, stderr, exit code, output file
and unresolved report byte-identical. Unit tests alone would pass a
seam that renumbered a line or reordered a report row.

tests/baselines/manifest.json holds no build-playlist case and is not
regenerated; this corpus is a separate directory.

Recording: set BUILD_PLAYLIST_TEXT_RECORD=1 and run this file once, at
the commit the corpus README names. A normal suite run only replays.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.conftest import run_tool

CORPUS = Path(__file__).resolve().parent / "baselines" / "build_playlist_text"
RECORD = os.environ.get("BUILD_PLAYLIST_TEXT_RECORD") == "1"

# playlists.synthesize_playlist_node stamps uuid.uuid4() onto every
# synthesized PLAYLIST node (DL-029); a fixed value leaves the corpus
# comparing behaviour rather than randomness.
_FIXED_UUID = uuid.UUID("00000000-0000-4000-8000-000000000000")


def _entry(artist: str, title: str, filename: str, folder: str = "Music") -> str:
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="/:{folder}/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
        '<INFO BITRATE="320" PLAYTIME_FLOAT="200.0" FILESIZE="8000"></INFO>'
        "</ENTRY>"
    )


def _base_nml() -> str:
    # "Dup - Twice" is held at two locations so a line naming it is
    # ambiguous; the "Sets" FOLDER gives --target-folder a found case.
    entries = (
        _entry("Alpha", "One", "alpha-one.mp3")
        + _entry("Beta", "Two", "beta-two.mp3")
        + _entry("Gamma", "Three", "gamma-three.mp3")
        + _entry("Dup", "Twice", "dup-a.mp3", "A")
        + _entry("Dup", "Twice", "dup-b.mp3", "B")
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="5">{entries}</COLLECTION>'
        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="1">'
        '<NODE TYPE="FOLDER" NAME="Sets"><SUBNODES COUNT="0"></SUBNODES></NODE>'
        "</SUBNODES></NODE></PLAYLISTS>"
        "<SETS></SETS><INDEXING></INDEXING></NML>"
    )


_CLEAN = b"Alpha - One\nBeta - Two\n"

# (case name, track-list bytes or None for no file, extra argv)
CASES: list[tuple[str, bytes | None, list[str]]] = [
    ("clean", _CLEAN, []),
    ("unparseable", b"Alpha - One\nno delimiter here\nBeta - Two\n", []),
    ("unparseable_allowed", b"Alpha - One\nno delimiter here\nBeta - Two\n", ["--allow-unmatched"]),
    ("ambiguous", b"Alpha - One\nDup - Twice\n", []),
    ("unmatched", b"Alpha - One\nNobody - Nothing\n", []),
    ("unmatched_allowed", b"Alpha - One\nNobody - Nothing\n", ["--allow-unmatched"]),
    ("duplicates", b"Alpha - One\nAlpha - One\nBeta - Two\n", []),
    ("utf8_bom", b"\xef\xbb\xbfAlpha - One\nBeta - Two\n", []),
    ("track_number_prefix", b"1 - Alpha - One\n02 - Beta - Two\n", []),
    ("comments_and_blanks", b"# set list\n\nAlpha - One\n   \n# end\nBeta - Two\n", []),
    ("target_folder_found", _CLEAN, ["--target-folder", "Sets"]),
    ("target_folder_missing", _CLEAN, ["--target-folder", "Nowhere"]),
    ("target_folder_root", _CLEAN, ["--target-folder", "$ROOT"]),
    ("full_collection", _CLEAN, ["--full-collection"]),
    ("dry_run", _CLEAN, ["--dry-run"]),
    ("unresolved_report", b"Alpha - One\nNobody - Nothing\nno delimiter\n", ["--allow-unmatched", "--unresolved-report", "unresolved.csv"]),
    ("zero_resolved", b"Nobody - Nothing\n", ["--allow-unmatched"]),
    ("decode_error", b"Alpha - One\n\xff\xfe\xfa\n", []),
    ("missing_tracklist", None, []),
]


def _invoke(tmp_path: Path, tracklist: bytes | None, extra: list[str]):
    (tmp_path / "base.nml").write_text(_base_nml(), encoding="utf-8", newline="")
    if tracklist is not None:
        (tmp_path / "tracks.txt").write_bytes(tracklist)
    # Relative paths under cwd=tmp_path keep every path the CLI prints
    # identical between the recording run and any replay.
    argv = ["build-playlist", "base.nml", "tracks.txt", "out.nml", "--name", "Set", *extra]
    with patch("uuid.uuid4", return_value=_FIXED_UUID):
        result = run_tool(argv, cwd=tmp_path)
    return argv, result


def _observed(tmp_path: Path, argv, result) -> dict[str, bytes]:
    files = {
        "argv.json": json.dumps(argv).encode("utf-8"),
        "stdout.txt": result.stdout.encode("utf-8"),
        "stderr.txt": result.stderr.encode("utf-8"),
        "exit_code.txt": str(result.exit_code).encode("utf-8"),
    }
    # Absent under a refusal or --dry-run; its absence is part of the record.
    for written in ("out.nml", "unresolved.csv"):
        path = tmp_path / written
        if path.exists():
            files["output.nml" if written == "out.nml" else written] = path.read_bytes()
    return files


@pytest.mark.parametrize("case,tracklist,extra", CASES, ids=[c[0] for c in CASES])
def test_text_path_replays_its_recorded_corpus(tmp_path: Path, case, tracklist, extra):
    r"""Every recorded case replays byte-identically: the same argv, the
    same stdout and stderr, the same exit code, the same output file and
    unresolved report, and no file the recording did not write.

    Mutation: tracklist.text_candidates builds each unparseable
        Candidate with line.line_number - 1, so the unresolved_report
        case prints its unparseable row as line=2 rather than line=3 and
        its stdout.txt differs from the recording.
    Observed:
        E   AssertionError: stdout.txt differs for unresolved_report
        E   assert 'lines_read=3...ten=out.nml\n' == 'lines_read=3...ten=out.nml\n'
        E     
        E     Skipping 200 identical leading characters in diff, use -v to show
        E     Skipping 93 identical trailing characters in diff, use -v to show
        E     - lved line=3 kind=unp
        E     ?           ^
        E     + lved line=2 kind=unp
        E     ?           ^
    """
    argv, result = _invoke(tmp_path, tracklist, extra)
    observed = _observed(tmp_path, argv, result)
    case_dir = CORPUS / case

    if RECORD:
        case_dir.mkdir(parents=True, exist_ok=True)
        for name, data in observed.items():
            (case_dir / name).write_bytes(data)
        return

    assert case_dir.is_dir(), f"corpus case {case} was never recorded"
    recorded = {path.name: path.read_bytes() for path in case_dir.iterdir()}
    assert sorted(observed) == sorted(recorded), f"file set differs for {case}"
    for name, data in recorded.items():
        assert observed[name].decode("utf-8", "replace") == data.decode("utf-8", "replace"), (
            f"{name} differs for {case}"
        )
        assert observed[name] == data, f"{name} bytes differ for {case}"


def test_corpus_holds_every_case_and_nothing_else():
    """The corpus directory holds a subdirectory for exactly the cases
    above, so a case dropped from CASES cannot silently stop being
    replayed while its recording lingers.

    Mutation: the recorded corpus loses its
        tests/baselines/build_playlist_text/dry_run/ directory, so the
        directories on disk no longer equal the CASES names.
    Observed:
        E   AssertionError: assert ['ambiguous',...lection', ...] == ['ambiguous',...licates', ...]
        E     
        E     At index 4 diff: 'duplicates' != 'dry_run'
        E     Right contains one more item: 'zero_resolved'
        E     Use -v to get more diff
    """
    if RECORD:
        pytest.skip("recording run")
    on_disk = sorted(path.name for path in CORPUS.iterdir() if path.is_dir())
    assert on_disk == sorted(case for case, _t, _e in CASES)
