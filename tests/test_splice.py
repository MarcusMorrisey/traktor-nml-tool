"""Splice: playlist merge, name collision, and conflict abort/report."""

from __future__ import annotations

import re
from pathlib import Path

from tests.conftest import run_tool


def _nml(entries_xml: str, entries_count: int, playlists_xml: str, sorting_info_xml: str = "") -> str:
    """Minimal NML wrapper whose SUBNODES COUNT is derived by counting
    literal '<NODE' occurrences in playlists_xml, so a caller only ever
    authors the inner playlist XML once."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
        f'<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="{playlists_xml.count(chr(60)+"NODE")}">'
        f"{playlists_xml}</SUBNODES></NODE></PLAYLISTS>"
        f"<SETS></SETS><INDEXING>{sorting_info_xml}</INDEXING></NML>"
    )


def _entry(artist, title, filename, size="16", time="1.0"):
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="/:Music/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
        f'<INFO BITRATE="320" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
        "</ENTRY>"
    )


def _playlist(name: str, keys: list[str], uuid: str) -> str:
    entries = "".join(f'<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="{k}"></PRIMARYKEY></ENTRY>' for k in keys)
    return (
        f'<NODE TYPE="PLAYLIST" NAME="{name}">'
        f'<PLAYLIST ENTRIES="{len(keys)}" TYPE="LIST" UUID="{uuid}">{entries}</PLAYLIST>'
        "</NODE>"
    )


def _playlist_no_uuid(name: str, keys: list[str]) -> str:
    """A PLAYLIST child with no UUID attribute at all - locating this node
    by a UUID text search (the old _locate_node_start behavior) would fail
    outright; identity-based location via SpanIndex does not depend on it."""
    entries = "".join(f'<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="{k}"></PRIMARYKEY></ENTRY>' for k in keys)
    return (
        f'<NODE TYPE="PLAYLIST" NAME="{name}">'
        f'<PLAYLIST ENTRIES="{len(keys)}" TYPE="LIST">{entries}</PLAYLIST>'
        "</NODE>"
    )


def test_splicing_all_unique_playlists_merges_cleanly(tmp_path: Path) -> None:
    base_key = "C:" + "/:Music/:" + "base.mp3"
    other_key = "C:" + "/:Music/:" + "other.mp3"

    base_path = tmp_path / "base.nml"
    base_path.write_text(
        _nml(_entry("A", "Base", "base.mp3"), 1, _playlist("BaseList", [base_key], "uuid-base")),
        encoding="utf-8", newline="",
    )
    other_path = tmp_path / "other.nml"
    other_path.write_text(
        _nml(_entry("B", "Other", "other.mp3"), 1, _playlist("OtherList", [other_key], "uuid-other")),
        encoding="utf-8", newline="",
    )

    result = run_tool(
        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path)],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    out_text = (tmp_path / "out.nml").read_text(encoding="utf-8")
    assert "OtherList" in out_text
    assert "BaseList" in out_text
    assert 'ENTRIES="2"' in out_text.split("COLLECTION")[1][:40]


def test_name_collision_gets_renamed_and_new_uuid(tmp_path: Path) -> None:
    base_key = "C:" + "/:Music/:" + "base.mp3"
    other_key = "C:" + "/:Music/:" + "other.mp3"

    base_path = tmp_path / "base.nml"
    base_path.write_text(
        _nml(_entry("A", "Base", "base.mp3"), 1, _playlist("Shared", [base_key], "uuid-base")),
        encoding="utf-8", newline="",
    )
    other_path = tmp_path / "other.nml"
    other_path.write_text(
        _nml(_entry("B", "Other", "other.mp3"), 1, _playlist("Shared", [other_key], "uuid-other")),
        encoding="utf-8", newline="",
    )

    result = run_tool(
        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path)],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    out_text = (tmp_path / "out.nml").read_text(encoding="utf-8")
    assert 'NAME="Shared (2)"' in out_text
    assert "uuid-other" not in out_text  # renamed playlist got a fresh UUID
    assert out_text.count('NAME="Shared"') == 1  # base's own playlist untouched


def test_unresolved_conflict_without_policy_aborts_but_still_reports(tmp_path: Path) -> None:
    shared_key = "C:" + "/:Music/:" + "track.mp3"

    base_path = tmp_path / "base.nml"
    base_path.write_text(
        _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, ""),
        encoding="utf-8", newline="",
    )
    other_path = tmp_path / "other.nml"
    # Same artist/title/filesize/time key (matches artist_title_size_time
    # tier) but a different bitrate - a divergent attribute between the two
    # copies of "the same" track.
    other_path.write_text(
        _nml(_entry("A", "Song", "track.mp3", time="100.0").replace('BITRATE="320"', 'BITRATE="128"'), 1, ""),
        encoding="utf-8", newline="",
    )

    result = run_tool(
        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path),
         "--conflict-report", str(tmp_path / "conflicts.csv")],
        cwd=tmp_path,
    )
    assert result.exit_code == 2
    assert not (tmp_path / "out.nml").exists()
    assert (tmp_path / "conflicts.csv").exists()


def test_conflict_resolved_with_on_conflict_keep_first_still_writes_report(tmp_path: Path) -> None:
    base_path = tmp_path / "base.nml"
    base_path.write_text(_nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, ""), encoding="utf-8", newline="")
    other_path = tmp_path / "other.nml"
    other_path.write_text(
        _nml(_entry("A", "Song", "track.mp3", time="100.0").replace('BITRATE="320"', 'BITRATE="128"'), 1, ""),
        encoding="utf-8", newline="",
    )

    result = run_tool(
        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path),
         "--on-conflict", "keep-first", "--conflict-report", str(tmp_path / "conflicts.csv")],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert (tmp_path / "out.nml").exists()
    assert (tmp_path / "conflicts.csv").exists()
    assert "conflict_key=" in result.stdout


def test_imported_playlist_sorting_info_is_rewritten_to_its_new_name(tmp_path: Path) -> None:
    base_key = "C:" + "/:Music/:" + "base.mp3"
    other_key = "C:" + "/:Music/:" + "other.mp3"

    base_path = tmp_path / "base.nml"
    base_path.write_text(
        _nml(
            _entry("A", "Base", "base.mp3"), 1,
            _playlist("BaseList", [base_key], "uuid-base") + _playlist("Shared", [base_key], "uuid-shared-base"),
            sorting_info_xml='<SORTING_INFO PATH="BaseList"></SORTING_INFO>',
        ),
        encoding="utf-8", newline="",
    )
    other_path = tmp_path / "other.nml"
    other_path.write_text(
        _nml(
            _entry("B", "Other", "other.mp3"), 1, _playlist("Shared", [other_key], "uuid-other"),
            sorting_info_xml='<SORTING_INFO PATH="Shared"><CRITERIA ATTRIBUTE="7" DIRECTION="0"></CRITERIA></SORTING_INFO>',
        ),
        encoding="utf-8", newline="",
    )

    result = run_tool(
        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path)],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    out_text = (tmp_path / "out.nml").read_text(encoding="utf-8")
    # The imported playlist collides with base's "Shared" playlist and is
    # renamed to "Shared (2)"; its own SORTING_INFO is carried into base's
    # INDEXING with its PATH rewritten to that renamed location, its
    # CRITERIA child untouched, and base's own SORTING_INFO left alone.
    assert 'NAME="Shared (2)"' in out_text
    assert 'PATH="Shared (2)"' in out_text
    assert 'ATTRIBUTE="7"' in out_text
    assert 'DIRECTION="0"' in out_text
    assert '<SORTING_INFO PATH="BaseList"></SORTING_INFO>' in out_text
    assert "sorting_info_dropped=[]" in result.stdout


def test_orphaned_sorting_info_is_reported_by_path_in_stats(tmp_path: Path) -> None:
    other_key = "C:" + "/:Music/:" + "other.mp3"

    base_path = tmp_path / "base.nml"
    base_path.write_text(
        _nml(_entry("A", "Base", "base.mp3"), 1, ""),
        encoding="utf-8", newline="",
    )
    other_path = tmp_path / "other.nml"
    other_path.write_text(
        _nml(
            _entry("B", "Other", "other.mp3"), 1, _playlist("OtherList", [other_key], "uuid-other"),
            sorting_info_xml='<SORTING_INFO PATH="Orphan"></SORTING_INFO>',
        ),
        encoding="utf-8", newline="",
    )

    result = run_tool(
        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path)],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    # "Orphan" matches no surviving/imported playlist's PATH, so it is
    # dropped and reported with its specific PATH value, not just a count.
    assert "sorting_info_dropped=['Orphan']" in result.stdout


def test_contribution_playlist_with_no_uuid_is_imported_verbatim(tmp_path: Path) -> None:
    other_key = "C:" + "/:Music/:" + "other.mp3"

    base_path = tmp_path / "base.nml"
    base_path.write_text(
        _nml(_entry("A", "Base", "base.mp3"), 1, ""),
        encoding="utf-8", newline="",
    )
    other_path = tmp_path / "other.nml"
    other_path.write_text(
        _nml(_entry("B", "Other", "other.mp3"), 1, _playlist_no_uuid("NoUuid", [other_key])),
        encoding="utf-8", newline="",
    )

    result = run_tool(
        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path)],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    out_text = (tmp_path / "out.nml").read_text(encoding="utf-8")
    assert 'NAME="NoUuid"' in out_text
    assert other_key in out_text


# --- playlist reconstruction (DL-091..DL-103) ---------------------------------
#
# Every guard below drives the CLI, so it exercises the --reconstruct-playlists
# flag, assemble_output's pre-pass and the import exclusion together rather than
# any one of them alone.

_E3 = _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3") + _entry("C", "Three", "three.mp3")


def _key(name: str) -> str:
    return "C:" + "/:Music/:" + name + ".mp3"


def _write_nml(path: Path, playlists_xml: str) -> Path:
    path.write_text(_nml(_E3, 3, playlists_xml), encoding="utf-8", newline="")
    return path


def _reconstruct(tmp_path: Path, base_xml: str, *input_xml: str, flag: bool = True):
    base_path = _write_nml(tmp_path / "base.nml", base_xml)
    before = base_path.read_bytes()
    argv = ["splice", str(base_path), str(tmp_path / "out.nml")]
    for i, xml in enumerate(input_xml):
        argv += ["--input", str(_write_nml(tmp_path / ("in%d.nml" % i), xml))]
    if flag:
        argv.append("--reconstruct-playlists")
    result = run_tool(argv, cwd=tmp_path)
    out_path = tmp_path / "out.nml"
    text = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    # The base input is never rewritten. Asserted on every path, so a
    # reconstruction that edited its own source would fail here first.
    assert base_path.read_bytes() == before, "base input was modified"
    return result, text


def _names(text: str) -> list:
    return re.findall(r'NODE TYPE="PLAYLIST" NAME="([^"]*)"', text)


def _pkeys(text: str) -> list:
    return re.findall(r'PRIMARYKEY TYPE="TRACK" KEY="([^"]*)"', text)


def test_empty_base_playlist_is_filled_from_the_same_named_source(tmp_path: Path) -> None:
    """The reconstruction case: base carries the playlist NAME with no
    entries, and an older collection holds its contents.

    Observed without --reconstruct-playlists, against these same two files:
    NAMEs ['MySet', 'MySet (2)'] with ENTRIES ['0', '2'] at exit code 0 -
    base's own list stays empty and the tracks land in a renamed duplicate
    beside it. test_the_flag_is_required_to_reconstruct pins that unflagged
    behaviour as the default.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("MySet", [], "uuid-base"),
        _playlist("MySet", [_key("one"), _key("two")], "uuid-prev"),
    )
    assert result.exit_code == 0
    assert _names(text) == ["MySet"], "a renamed duplicate accompanied the reconstruction"
    assert _pkeys(text) == [_key("one"), _key("two")]
    assert "uuid-base" in text, "base playlist did not keep its own UUID"


def test_same_count_divergent_contents_union_to_base_first_order(tmp_path: Path) -> None:
    """Base [one, two] and incoming [two, three] hold the same number of
    entries but not the same ones.

    Observed against an entry-count trigger (the rule this replaced,
    reconstructing only when the counts differ): playlists_reconstructed=0
    and the playlist left as [one, two], because 2 == 2 - the divergence is
    invisible to counting.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("MySet", [_key("one"), _key("two")], "uuid-base"),
        _playlist("MySet", [_key("two"), _key("three")], "uuid-prev"),
    )
    assert result.exit_code == 0
    assert _pkeys(text) == [_key("one"), _key("two"), _key("three")]


def test_identical_ordered_contents_leave_base_untouched_and_import_nothing(tmp_path: Path) -> None:
    """Nothing to reconstruct, and nothing to add.

    Observed while the import exclusion covered only reconstructed names:
    NAMEs ['MySet', 'MySet (2)'] - base was correctly untouched, but the
    incoming copy still fell through to the rename path, leaving a
    duplicate holding exactly what base already held.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("MySet", [_key("one")], "uuid-base"),
        _playlist("MySet", [_key("one")], "uuid-prev"),
    )
    assert result.exit_code == 0
    assert _names(text) == ["MySet"]
    assert _pkeys(text) == [_key("one")]


def test_a_reordering_triggers_reconstruction_into_base_order(tmp_path: Path) -> None:
    """Same tracks, different order, counts equal.

    Observed while the trigger compared base against the MERGED sequence
    rather than against the incoming one: playlists_reconstructed=0 and no
    rebuild at all. Merging puts base's keys first, so a merged sequence can
    never differ from base whenever both sides hold the same tracks - the
    ordering difference was structurally unreachable.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("MySet", [_key("two"), _key("one")], "uuid-base"),
        _playlist("MySet", [_key("one"), _key("two")], "uuid-prev"),
    )
    assert result.exit_code == 0
    assert _pkeys(text) == [_key("two"), _key("one")], "base's own order was not preserved"


def test_two_inputs_are_folded_in_input_order(tmp_path: Path) -> None:
    """One name carried by two --input files folds both in, in the order
    given.

    Observed while the duplicate-NAME check counted names across all
    contributions rather than within each one: exit code 2 with
    'ambiguous_playlist_name playlist=MySet' and no output written - the
    fold this supports was rejected as an ambiguity.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("MySet", [], "uuid-base"),
        _playlist("MySet", [_key("one")], "uuid-a"),
        _playlist("MySet", [_key("three")], "uuid-b"),
    )
    assert result.exit_code == 0
    assert _pkeys(text) == [_key("one"), _key("three")]


def test_an_unmatched_base_name_is_left_alone(tmp_path: Path) -> None:
    """A base playlist with no same-named incoming one is not reconstructed,
    and the incoming playlist imports normally.

    Observed with the name lookup keyed on the incoming side instead of
    base: NAMEs ['Other'] with Other rebuilt from MySet's entries, giving
    base's unrelated playlist the source playlist's contents.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("Other", [_key("one")], "uuid-base"),
        _playlist("MySet", [_key("two")], "uuid-prev"),
    )
    assert result.exit_code == 0
    assert sorted(_names(text)) == ["MySet", "Other"]
    assert _pkeys(text) == [_key("one"), _key("two")]


def test_names_differing_only_in_case_are_distinct_playlists(tmp_path: Path) -> None:
    """Matching is exact and case-sensitive (DL-098).

    Observed with a casefolded name lookup: PRIMARYKEYs
    ['C:/:Music/:one.mp3', 'C:/:Music/:one.mp3'] instead of one - base's
    empty 's' is rebuilt from the unrelated 'S' while 'S' is still imported
    on its own name, so one track is reachable twice through two playlists
    that Traktor treats as distinct. The NAME assertion alone does not catch
    this: both names survive either way, and only the key count separates
    them.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("s", [], "uuid-base"),
        _playlist("S", [_key("one")], "uuid-prev"),
    )
    assert result.exit_code == 0
    assert sorted(_names(text)) == ["S", "s"]
    assert _pkeys(text) == [_key("one")], "base's 's' was rebuilt from the unrelated 'S'"


def test_a_duplicate_playlist_name_within_one_file_aborts(tmp_path: Path) -> None:
    """Two playlists sharing a NAME inside one document give no single
    playlist to reconstruct, so the run aborts with nothing written rather
    than picking one by document order (DL-098, following DL-008's
    abort-plus-report shape).

    Observed with the check disabled: exit code 0 rather than 2, so the run
    completes and writes an output instead of refusing a document-order
    guess between the two same-named base playlists.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("MySet", [], "uuid-base") + _playlist("MySet", [_key("one")], "uuid-base2"),
        _playlist("MySet", [_key("two")], "uuid-prev"),
    )
    assert result.exit_code == 2
    assert not (tmp_path / "out.nml").exists(), "output was written despite the abort"
    assert "ambiguous_playlist_name" in result.stderr


def test_the_flag_is_required_to_reconstruct(tmp_path: Path) -> None:
    """Without --reconstruct-playlists the collision rename stays the
    default, so existing splice invocations are unaffected (DL-095).

    Observed with reconstruction defaulted on: NAMEs ['MySet'] with
    ENTRIES ['1'] - every existing caller's output silently changing shape.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("MySet", [], "uuid-base"),
        _playlist("MySet", [_key("one")], "uuid-prev"),
        flag=False,
    )
    assert result.exit_code == 0
    assert _names(text) == ["MySet", "MySet (2)"]
