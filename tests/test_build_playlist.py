"""build-playlist: track-list resolution, playlist synthesis, and insertion."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from tests.conftest import run_tool


def _nml(entries_xml: str, entries_count: int, playlists_xml: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
        f'<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="{playlists_xml.count(chr(60)+"NODE")}">'
        f"{playlists_xml}</SUBNODES></NODE></PLAYLISTS>"
        "<SETS></SETS><INDEXING></INDEXING></NML>"
    )


def _nml_no_playlists_section(entries_xml: str = "", entries_count: int = 0) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
        "<SETS></SETS><INDEXING></INDEXING></NML>"
    )


def _entry(artist, title, filename, size="16", time="1.0"):
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="/:Music/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
        f'<INFO BITRATE="320" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
        "</ENTRY>"
    )


def _existing_playlist(name: str, keys: list[str], uuid: str) -> str:
    entries = "".join(f'<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="{k}"></PRIMARYKEY></ENTRY>' for k in keys)
    return (
        f'<NODE TYPE="PLAYLIST" NAME="{name}">'
        f'<PLAYLIST ENTRIES="{len(keys)}" TYPE="LIST" UUID="{uuid}">{entries}</PLAYLIST>'
        "</NODE>"
    )


def _folder(name: str, inner: str) -> str:
    return (
        f'<NODE TYPE="FOLDER" NAME="{name}">'
        f'<SUBNODES COUNT="{inner.count(chr(60)+"NODE")}">{inner}</SUBNODES>'
        "</NODE>"
    )


def _key(filename: str) -> str:
    return "C:" + "/:Music/:" + filename


def test_three_line_tracklist_writes_three_entries_in_input_order(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(
        _nml(_entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3") + _entry("C", "Three", "three.mp3"), 3, ""),
        encoding="utf-8", newline="",
    )
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\nB - Two\nC - Three\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--full-collection"],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert text.index(_key("one.mp3")) < text.index(_key("two.mp3")) < text.index(_key("three.mp3"))
    assert 'NAME="MyList"' in text


def test_default_output_is_a_single_playlist_with_only_its_collection_entries(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(
        _nml(_entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3"), 2, _existing_playlist("Other", [_key("two.mp3")], "uuid-other")),
        encoding="utf-8",
        newline="",
    )
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)

    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert 'ENTRIES="1"' in text
    assert 'NAME="MyList"' in text
    assert 'NAME="Other"' not in text
    assert _key("one.mp3") in text
    assert _key("two.mp3") not in text


def test_stats_report_lines_read_entries_written_and_playlist_name(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
    assert result.exit_code == 0
    assert "lines_read=1" in result.stdout
    assert "entries_written=1" in result.stdout
    assert "playlist_name=MyList" in result.stdout


def test_named_target_folder_receives_node_root_count_unchanged(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, _folder("MyFolder", "")), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        [
            "build-playlist", str(base), str(tracklist), str(out), "--name", "MyList",
            "--target-folder", "MyFolder", "--full-collection",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert 'NAME="MyFolder"' in text
    root_subnodes_count = text.split('SUBNODES COUNT="')[1].split('"')[0]
    assert root_subnodes_count == "1"


# a name collision aborts nothing (DL-029): it takes the numbered
# suffix and leaves the pre-existing playlist's own name and UUID alone
def test_name_collision_takes_numbered_suffix_original_untouched(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(
        _nml(_entry("A", "One", "one.mp3"), 1, _existing_playlist("MyList", [_key("one.mp3")], "uuid-existing")),
        encoding="utf-8", newline="",
    )
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--full-collection"], cwd=tmp_path
    )
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert 'NAME="MyList (2)"' in text
    assert 'NAME="MyList"' in text
    assert "uuid-existing" in text


def test_two_runs_yield_different_uuids(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")

    out1 = tmp_path / "out1.nml"
    out2 = tmp_path / "out2.nml"
    run_tool(["build-playlist", str(base), str(tracklist), str(out1), "--name", "MyList"], cwd=tmp_path)
    run_tool(["build-playlist", str(base), str(tracklist), str(out2), "--name", "MyList"], cwd=tmp_path)

    text1 = out1.read_text(encoding="utf-8")
    text2 = out2.read_text(encoding="utf-8")
    uuid1 = text1.split("PLAYLIST ENTRIES=")[1].split('UUID="')[1].split('"')[0]
    uuid2 = text2.split("PLAYLIST ENTRIES=")[1].split('UUID="')[1].split('"')[0]
    assert uuid1 != uuid2


def test_name_with_ampersand_and_quote_round_trips(tmp_path: Path) -> None:
    import xml.etree.ElementTree as ETree

    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", 'Rock & Roll "Classics"'], cwd=tmp_path
    )
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    root = ETree.fromstring(text.split("\n", 1)[1])
    names = [node.attrib.get("NAME") for node in root.findall(".//NODE[@TYPE='PLAYLIST']")]
    assert 'Rock & Roll "Classics"' in names


def test_dry_run_prints_stats_and_writes_nothing(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--dry-run"], cwd=tmp_path
    )
    assert result.exit_code == 0
    assert not out.exists()
    assert "entries_written=1" in result.stdout


def test_unmatched_line_aborts_writes_report_no_output(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\nGhost - Track\n", encoding="utf-8")
    out = tmp_path / "out.nml"
    report = tmp_path / "unresolved.csv"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--unresolved-report", str(report)],
        cwd=tmp_path,
    )
    assert result.exit_code == 2
    assert not out.exists()
    assert report.exists()


def test_allow_unmatched_writes_resolved_subset(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\nGhost - Track\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--allow-unmatched"], cwd=tmp_path
    )
    assert result.exit_code == 0
    assert out.exists()
    assert "entries_written=1" in result.stdout


def test_allow_unmatched_writes_report_alongside_successful_partial_build(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\nGhost - Track\n", encoding="utf-8")
    out = tmp_path / "out.nml"
    report = tmp_path / "unresolved.csv"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--allow-unmatched",
         "--unresolved-report", str(report)],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert out.exists()
    with report.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["kind"] == "unmatched"
    assert rows[0]["artist"] == "Ghost"


def test_absent_named_target_folder_aborts_no_output(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--target-folder", "DoesNotExist"],
        cwd=tmp_path,
    )
    assert result.exit_code == 2
    assert not out.exists()


def test_ambiguous_target_folder_name_aborts_no_output(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(
        _nml(_entry("A", "One", "one.mp3"), 1, _folder("Dup", "") + _folder("Wrapper", _folder("Dup", ""))),
        encoding="utf-8", newline="",
    )
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--target-folder", "Dup"],
        cwd=tmp_path,
    )
    assert result.exit_code == 2
    assert not out.exists()
    assert "target_folder_ambiguous=Dup:count=2" in result.stderr


def test_target_folder_naming_the_root_behaves_like_the_default(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--target-folder", "$ROOT"],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert out.exists()


def test_named_target_folder_with_no_subnodes_reports_distinct_error(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    malformed_folder = '<NODE TYPE="FOLDER" NAME="Empty"></NODE>'
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, malformed_folder), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--target-folder", "Empty"],
        cwd=tmp_path,
    )
    assert result.exit_code == 2
    assert not out.exists()
    assert "target_folder_no_subnodes" in result.stderr


def test_output_path_resolving_to_base_or_tracklist_is_refused(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")

    result = run_tool(["build-playlist", str(base), str(tracklist), str(base), "--name", "MyList"], cwd=tmp_path)
    assert result.exit_code == 2

    result = run_tool(["build-playlist", str(base), str(tracklist), str(tracklist), "--name", "MyList"], cwd=tmp_path)
    assert result.exit_code == 2


def test_malformed_base_reports_xml_parse_error(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text("<NML><unclosed>", encoding="utf-8")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--full-collection"], cwd=tmp_path
    )
    assert result.exit_code == 2
    assert "xml_parse_error" in result.stderr


def test_missing_tracklist_reports_input_not_found(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tmp_path / "missing.txt"), str(out), "--name", "MyList"], cwd=tmp_path
    )
    assert result.exit_code == 2
    assert "input_not_found" in result.stderr


def test_tracklist_path_pointing_at_a_directory_reports_input_not_found(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist_dir = tmp_path / "tracks.txt"
    tracklist_dir.mkdir()
    out = tmp_path / "out.nml"

    result = run_tool(["build-playlist", str(base), str(tracklist_dir), str(out), "--name", "MyList"], cwd=tmp_path)
    assert result.exit_code == 2
    assert "input_not_found" in result.stderr


def test_unresolved_report_path_with_missing_parent_dir_reports_write_error(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\nB - Two\n", encoding="utf-8")
    out = tmp_path / "out.nml"
    bad_report_path = tmp_path / "does_not_exist" / "report.csv"

    result = run_tool(
        [
            "build-playlist", str(base), str(tracklist), str(out),
            "--name", "MyList", "--allow-unmatched", "--unresolved-report", str(bad_report_path),
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 2
    assert "unresolved_report_write_error" in result.stderr
    assert not out.exists()


def test_empty_and_all_unparseable_and_all_unmatched_abort_with_no_output(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")

    empty_tracklist = tmp_path / "empty.txt"
    empty_tracklist.write_text("", encoding="utf-8")
    out1 = tmp_path / "out1.nml"
    result1 = run_tool(["build-playlist", str(base), str(empty_tracklist), str(out1), "--name", "MyList"], cwd=tmp_path)
    assert result1.exit_code == 2
    assert not out1.exists()

    all_unparseable = tmp_path / "unparseable.txt"
    all_unparseable.write_text("NoDelimiterHere\n", encoding="utf-8")
    out2 = tmp_path / "out2.nml"
    result2 = run_tool(["build-playlist", str(base), str(all_unparseable), str(out2), "--name", "MyList"], cwd=tmp_path)
    assert result2.exit_code == 2
    assert not out2.exists()

    all_unmatched = tmp_path / "unmatched.txt"
    all_unmatched.write_text("Ghost - Track\n", encoding="utf-8")
    out3 = tmp_path / "out3.nml"
    result3 = run_tool(
        ["build-playlist", str(base), str(all_unmatched), str(out3), "--name", "MyList", "--allow-unmatched"],
        cwd=tmp_path,
    )
    assert result3.exit_code == 2
    assert not out3.exists()


def test_base_with_no_playlists_section_aborts_with_no_root_subnodes(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(
        _nml_no_playlists_section(_entry("A", "One", "one.mp3"), 1), encoding="utf-8", newline=""
    )
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--full-collection"],
        cwd=tmp_path,
    )
    assert result.exit_code == 2
    assert "no_root_subnodes" in result.stderr
    assert not out.exists()


def test_duplicate_tracklist_lines_produce_two_entries_in_order(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\nA - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert text.count(_key("one.mp3")) == 2


def test_unresolved_csv_report_parses_back_with_matching_header(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("Ghost - Track\n", encoding="utf-8")
    out = tmp_path / "out.nml"
    report = tmp_path / "unresolved.csv"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--allow-unmatched",
         "--unresolved-report", str(report)],
        cwd=tmp_path,
    )
    assert result.exit_code == 2  # zero resolved lines: no_entries_resolved
    with report.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["kind"] == "unmatched"
    assert rows[0]["artist"] == "Ghost"


def test_primarykey_comes_from_matched_entry_not_input_text(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    key = text.split('KEY="')[1].split('"')[0]
    assert key == _key("one.mp3")
    assert "A" not in key.split("/")
    assert key != "A - One"


def test_output_bytes_outside_receiving_subnodes_match_base_exactly(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base_text = _nml(_entry("A", "One", "one.mp3"), 1, "")
    base.write_text(base_text, encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--full-collection"],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    out_text = out.read_text(encoding="utf-8")

    prefix_marker = '<SUBNODES COUNT="'
    suffix_marker = "</SUBNODES></NODE></PLAYLISTS>"
    base_prefix, base_rest = base_text.split(prefix_marker, 1)
    _, base_suffix = base_rest.split(suffix_marker, 1)
    out_prefix, out_rest = out_text.split(prefix_marker, 1)
    _, out_suffix = out_rest.split(suffix_marker, 1)

    assert out_prefix == base_prefix
    assert out_suffix == base_suffix


def test_matching_and_confidence_modules_are_byte_identical_to_pre_existing_contents() -> None:
    import traktor_nml.confidence as confidence
    import traktor_nml.matching as matching

    expected = {
        "matching.py": "b491a94d5d12c6ed82f1f02e3ac55e9badc932bdd1756474d7b9e2214fae0664",
        "confidence.py": "a9e5d6e3df16ae8787d3b05a8ce62ee6944683bcff66d2e33b9d4e988909890b",
    }
    for module, filename in ((matching, "matching.py"), (confidence, "confidence.py")):
        content = Path(module.__file__).read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        assert digest == expected[filename], f"{filename} changed - this feature must call the cascade, never edit it"


def test_commit_path_uses_write_bytes_atomically(tmp_path: Path, monkeypatch) -> None:
    from traktor_nml.commands import build_playlist_cmd

    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\n", encoding="utf-8")
    out = tmp_path / "out.nml"

    calls = []
    original = build_playlist_cmd.write_bytes_atomically

    def _spy(path, data):
        calls.append((path, data))
        original(path, data)

    monkeypatch.setattr(build_playlist_cmd, "write_bytes_atomically", _spy)

    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
    assert result.exit_code == 0
    assert len(calls) == 1
    assert calls[0][0] == out


def test_no_forbidden_imports_or_substrings_in_new_modules() -> None:
    import traktor_nml.buildplaylist as buildplaylist
    import traktor_nml.tracklist as tracklist
    from traktor_nml.commands import build_playlist_cmd

    forbidden = ("pyacoustid", "chromaprint", "fpcalc", "requests", "urllib.request", ".m3u", ".m3u8")
    for module in (buildplaylist, tracklist, build_playlist_cmd):
        source = Path(module.__file__).read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in source


def test_abort_never_creates_or_modifies_a_pre_existing_output_path(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("Ghost - Track\n", encoding="utf-8")
    out = tmp_path / "out.nml"
    sentinel = "PRE-EXISTING CONTENT THAT MUST SURVIVE AN ABORT"
    out.write_text(sentinel, encoding="utf-8")

    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
    assert result.exit_code == 2
    assert out.read_text(encoding="utf-8") == sentinel


def test_unresolved_report_path_resolving_to_an_input_is_refused(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_text("A - One\nGhost - Track\n", encoding="utf-8")
    out = tmp_path / "out.nml"
    base_sentinel = base.read_text(encoding="utf-8")

    result = run_tool(
        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--unresolved-report", str(base)],
        cwd=tmp_path,
    )
    assert result.exit_code == 2
    assert not out.exists()
    assert base.read_text(encoding="utf-8") == base_sentinel


def test_non_utf8_tracklist_reports_decode_error(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_bytes("Björk - Jöga\n".encode("cp1252"))
    out = tmp_path / "out.nml"

    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
    assert result.exit_code == 2
    assert "tracklist_decode_error" in result.stderr
    assert not out.exists()


def test_utf8_bom_prefixed_tracklist_parses_first_line_cleanly(tmp_path: Path) -> None:
    base = tmp_path / "base.nml"
    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
    tracklist = tmp_path / "tracks.txt"
    tracklist.write_bytes("A - One\n".encode("utf-8-sig"))
    out = tmp_path / "out.nml"

    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
    assert result.exit_code == 0
    assert "entries_written=1" in result.stdout
    text = out.read_text(encoding="utf-8")
    assert _key("one.mp3") in text
