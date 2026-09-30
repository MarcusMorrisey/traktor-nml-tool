"""Contract checks for the extracted package: subcommand surface and the
--allow-artist-title-only / --match-confidence loose equivalence (DL-010)."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import run_tool


def test_help_lists_every_pre_existing_subcommand(tmp_path: Path) -> None:
    """The seven subcommands that predate the package extraction all survive it.

    Checked as a subset, not an exact set: later milestones (reconnect,
    splice, split) add their own subcommands to the same discovery
    mechanism, and this test's job is only to catch the extraction itself
    silently dropping or renaming one of the original seven.
    """
    result = run_tool(["--help"], cwd=tmp_path)
    expected = {
        "inspect",
        "encode-dir",
        "preview-diff",
        "preview-compare",
        "scan-compare-candidates",
        "rewrite",
        "rewrite-from-collection-compare",
    }
    # argparse's {a,b,c} choices list is the definitive subcommand set.
    brace_start = result.stdout.index("{")
    brace_end = result.stdout.index("}", brace_start)
    listed = set(result.stdout[brace_start + 1:brace_end].split(","))
    assert expected <= listed


def test_allow_artist_title_only_matches_loose_confidence(fixture_corpus: Path, tmp_path: Path) -> None:
    """Byte-identical stdout between the two invocations confirms
    --allow-artist-title-only is a pure alias for --match-confidence
    loose (DL-010)."""
    legacy = run_tool(
        ["preview-compare", str(fixture_corpus / "duplicate_rips.nml"), str(fixture_corpus / "duplicate_rips.nml"),
         "--allow-artist-title-only"],
        cwd=tmp_path,
    )
    enum_form = run_tool(
        ["preview-compare", str(fixture_corpus / "duplicate_rips.nml"), str(fixture_corpus / "duplicate_rips.nml"),
         "--match-confidence", "loose"],
        cwd=tmp_path,
    )
    assert legacy.stdout == enum_form.stdout


def test_splice_malformed_base_reports_xml_parse_error(tmp_path: Path) -> None:
    base_path = tmp_path / "base.nml"
    base_path.write_text("<NML VERSION=\"20\"><UNCLOSED>", encoding="utf-8")
    other_path = tmp_path / "other.nml"
    other_path.write_text('<?xml version="1.0"?><NML VERSION="20"></NML>', encoding="utf-8")
    out_path = tmp_path / "out.nml"

    result = run_tool(
        ["splice", str(base_path), str(out_path), "--input", str(other_path)], cwd=tmp_path
    )
    assert result.exit_code == 2
    assert f"xml_parse_error={base_path.as_posix()}" in result.stderr
    assert not out_path.exists()


def test_splice_malformed_contribution_reports_xml_parse_error(tmp_path: Path) -> None:
    base_path = tmp_path / "base.nml"
    base_path.write_text('<?xml version="1.0"?><NML VERSION="20"></NML>', encoding="utf-8")
    good_path = tmp_path / "good.nml"
    good_path.write_text('<?xml version="1.0"?><NML VERSION="20"></NML>', encoding="utf-8")
    bad_path = tmp_path / "bad.nml"
    bad_path.write_text("<NML VERSION=\"20\"><UNCLOSED>", encoding="utf-8")
    out_path = tmp_path / "out.nml"

    result = run_tool(
        ["splice", str(base_path), str(out_path), "--input", str(good_path), "--input", str(bad_path)],
        cwd=tmp_path,
    )
    assert result.exit_code == 2
    assert f"xml_parse_error={bad_path.as_posix()}" in result.stderr
    assert not out_path.exists()


def test_split_malformed_input_reports_xml_parse_error(tmp_path: Path) -> None:
    src_path = tmp_path / "src.nml"
    src_path.write_text("<NML VERSION=\"20\"><UNCLOSED>", encoding="utf-8")
    out_path = tmp_path / "out.nml"

    result = run_tool(["split", str(src_path), "--group", str(out_path), "Keep"], cwd=tmp_path)
    assert result.exit_code == 2
    assert f"xml_parse_error={src_path.as_posix()}" in result.stderr
    assert not out_path.exists()


def test_inspect_malformed_input_reports_xml_parse_error(tmp_path: Path) -> None:
    src_path = tmp_path / "src.nml"
    src_path.write_text("<NML VERSION=\"20\"><UNCLOSED>", encoding="utf-8")

    result = run_tool(["inspect", str(src_path)], cwd=tmp_path)
    assert result.exit_code == 2
    assert f"xml_parse_error={src_path.as_posix()}" in result.stderr


def test_preview_diff_malformed_input_reports_xml_parse_error(tmp_path: Path) -> None:
    src_path = tmp_path / "src.nml"
    src_path.write_text("<NML VERSION=\"20\"><UNCLOSED>", encoding="utf-8")

    result = run_tool(
        ["preview-diff", str(src_path), "--rule", "OldVol", "/old/", "NewVol", "/new/"], cwd=tmp_path
    )
    assert result.exit_code == 2
    assert f"xml_parse_error={src_path.as_posix()}" in result.stderr


def test_scan_reconnect_candidates_malformed_input_reports_xml_parse_error(tmp_path: Path) -> None:
    src_path = tmp_path / "src.nml"
    src_path.write_text("<NML VERSION=\"20\"><UNCLOSED>", encoding="utf-8")
    scan_dir = tmp_path / "scan"
    scan_dir.mkdir()

    result = run_tool(
        ["scan-reconnect-candidates", str(src_path), "--scan-root", str(scan_dir)], cwd=tmp_path
    )
    assert result.exit_code == 2
    assert f"xml_parse_error={src_path.as_posix()}" in result.stderr


def test_interrupted_commit_leaves_destination_and_no_temp_file(tmp_path: Path, monkeypatch) -> None:
    """Seed the destination with a valid collection, inject an OSError
    into the commit's own os.replace call, and confirm the destination
    still holds exactly its original bytes with no temp file left beside
    it - without the injected raise there is no interruption to observe
    and this assertion could not fail."""
    import traktor_nml.rewrite as rewrite_module

    # A structurally complete NML (COLLECTION plus a root PLAYLISTS/SUBNODES)
    # is required here, not just well-formed XML: assemble_output aborts
    # with no_collection before any write is attempted against a document
    # missing COLLECTION, which would never exercise the injected os.replace
    # failure below and let this test's assertions pass vacuously.
    valid_nml = (
        '<?xml version="1.0"?><NML VERSION="20"><COLLECTION ENTRIES="0"></COLLECTION>'
        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS>'
        "<SETS></SETS><INDEXING></INDEXING></NML>"
    )
    base_path = tmp_path / "base.nml"
    base_path.write_text(valid_nml, encoding="utf-8")
    other_path = tmp_path / "other.nml"
    other_path.write_text(valid_nml, encoding="utf-8")
    out_path = tmp_path / "out.nml"
    seeded_bytes = b"previous complete collection bytes"
    out_path.write_bytes(seeded_bytes)

    def _raise(*_args, **_kwargs):
        raise OSError("simulated interrupted commit")

    monkeypatch.setattr(rewrite_module.os, "replace", _raise)

    result = run_tool(
        ["splice", str(base_path), str(out_path), "--input", str(other_path)], cwd=tmp_path
    )
    assert result.exit_code != 0
    assert out_path.read_bytes() == seeded_bytes
    leftover = [p for p in tmp_path.iterdir() if p.name.startswith(f".{out_path.name}.")]
    assert leftover == []


def test_build_playlist_help_lists_csv_columns_from_their_definition(tmp_path):
    """--help names every CSV_COLUMNS header and the --input-format
    choices, read from the definition rather than restated (DL-294).

    Mutation: the --input-format argument's choices drop 'folder', so
        --help prints {auto,text,csv,m3u} in place of
        {auto,text,csv,m3u,folder}.
    Observed:
        E       AssertionError: assert '{auto,text,csv,m3u,folder}' in 'usage: python.exe -m pytest build-playlist [-h] --name NAME [--input-format {auto,text,csv,m3u}] [--target-folder TAR...ORT --dry-run Skip the write to the NML output file. Any report or CSV side file this command writes is still written.'
    """
    from traktor_nml.playlistinput import CSV_COLUMNS

    result = run_tool(["build-playlist", "--help"], cwd=tmp_path)
    assert result.exit_code == 0
    flat = " ".join(result.stdout.split())
    for column in CSV_COLUMNS:
        assert column.header in flat
    assert "{auto,text,csv,m3u,folder}" in flat


# The settled reading on the command's own stdout. These guards invoke the
# subcommand for real rather than calling assemble_output, because what a
# caller parses is the printed line and the exit code, not the row behind
# it: a stats key renamed or a line reworded is a contract change even
# where every row is right (DL-215).
#
# Each guard's docstring carries the mutation applied to make it fail and
# the verbatim stdout observed under that mutation, quoted rather than
# paraphrased: a guard whose recorded failure is a paraphrase cannot be
# distinguished from one green in exactly the broken state (DL-189).
#
# The measured attribute names are read off traktor_nml.metadata_tier
# here rather than imported into splice_cmd.py, so no name stands in the
# command that its production code does not call (DL-326).


def _collection(entries_xml: str, count: int) -> str:
    """The minimal NML a splice run reads, carrying count collection
    entries and no playlist. Written here rather than imported from the
    splice unit suite so this file's guards own the fixture whose
    BITRATE they move."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{count}">{entries_xml}</COLLECTION>'
        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0">'
        "</SUBNODES></NODE></PLAYLISTS>"
        "<SETS></SETS><INDEXING></INDEXING></NML>"
    )


def _entry_xml(artist: str, filename: str, bitrate: str = "320") -> str:
    """One ENTRY carrying every tracked attribute, at a LOCATION the
    identity key is derived from."""
    return (
        f'<ENTRY TITLE="Song" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="/:Music/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
        f'<INFO BITRATE="{bitrate}" PLAYTIME_FLOAT="100.0" FILESIZE="16"></INFO>'
        "</ENTRY>"
    )


def _write_pair(tmp_path: Path, name: str, base_xml: str, source_xml: str, count: int):
    """A (base path, source path, output path) triple written LF-clean."""
    base = tmp_path / f"{name}_base.nml"
    base.write_text(_collection(base_xml, count), encoding="utf-8", newline="")
    source = tmp_path / f"{name}_source.nml"
    source.write_text(_collection(source_xml, count), encoding="utf-8", newline="")
    return base, source, tmp_path / f"{name}_out.nml"


def _measured_only_pair(tmp_path: Path):
    """Two copies of one track diverging in BITRATE alone - a group the
    tier settles with no editorial judgement to ask for, and a 320/128
    spread far enough past OUTLIER_BAND to be worth reading."""
    return _write_pair(
        tmp_path, "measured",
        _entry_xml("A", "one.mp3"),
        _entry_xml("A", "one.mp3", bitrate="128"),
        1,
    )


def _identical_pair(tmp_path: Path):
    """Two byte-identical copies: one identity group, nothing divergent,
    so the rule settles nothing."""
    return _write_pair(tmp_path, "same", _entry_xml("A", "one.mp3"), _entry_xml("A", "one.mp3"), 1)


def _mixed_pair(tmp_path: Path):
    """One group diverging in ARTIST alone, which is an editorial
    judgement and so a conflict, beside one diverging in BITRATE alone,
    which the rule settles. Returns the triple plus a report path."""
    base, source, out = _write_pair(
        tmp_path, "mixed",
        _entry_xml("A", "one.mp3") + _entry_xml("B", "two.mp3"),
        _entry_xml("A", "one.mp3", bitrate="128") + _entry_xml("B2", "two.mp3"),
        2,
    )
    return base, source, out, tmp_path / "conflicts.csv"


def _splice(tmp_path: Path, base: Path, out: Path, source: Path, *extra: str):
    return run_tool(
        ["splice", str(base), str(out), "--input", str(source), *extra], cwd=tmp_path
    )


def test_a_measured_only_pair_exits_zero_and_prints_the_settled_count(tmp_path: Path) -> None:
    """The subcommand invoked for real over a pair diverging in BITRATE
    alone exits 0 and prints groups_settled_by_rule with the rest of the
    run's stats: the count a reader's sentence reads is the count the
    command prints (DL-215).

    Fail-first mutation: splice.py's stats key spelled settled_groups.
    Observed:
        E       AssertionError: assert 'groups_settled_by_rule=1' in 'inputs_merged=1\nidentity_groups=1\nconflicts_reported=0\nsettled_groups=1\nsettled_groups_outlying=1\ncollection_ent...itten=C:/Users/marcu/AppData/Local/Temp/pytest-of-marcu/pytest-1521/test_a_measured_only_pair_exit0/measured_out.nml'
    """
    base, source, out = _measured_only_pair(tmp_path)
    result = _splice(tmp_path, base, out, source)
    assert result.exit_code == 0
    assert "groups_settled_by_rule=1" in result.stdout
    assert "conflicts_reported=0" in result.stdout


def test_every_settled_outlier_line_names_a_measured_attribute(tmp_path: Path) -> None:
    """One line per wide measured gap, under the stats block, naming the
    attribute, the two values, the relative gap and the record the output
    keeps - named by the input index it was read from and its primary
    key, never a base-or-source token, and never the key alone, which
    both members of a settled group carry (DL-148, DL-330).

    The attribute names are checked against metadata_tier.MEASURED_ATTRS
    read here rather than imported into the command, so no name stands in
    splice_cmd.py that its production code does not call.

    Fail-first mutation: the printed line's two winner fields replaced by
    a single f" winner=base".
    Observed:
        E       AssertionError: assert 'winner_input=0 winner_key=C:/:Music/:one.mp3' in 'settled_outlier key=C:/:Music/:one.mp3 attr=bitrate low=128 high=320 relative_gap=0.6000 winner=base'
    """
    from traktor_nml.metadata_tier import MEASURED_ATTRS

    base, source, out = _measured_only_pair(tmp_path)
    result = _splice(tmp_path, base, out, source)
    assert result.exit_code == 0
    lines = [line for line in result.stdout.splitlines() if line.startswith("settled_outlier ")]
    assert len(lines) == 1
    assert "attr=bitrate" in lines[0]
    assert all(any(f"attr={attr}" in line for attr in MEASURED_ATTRS) for line in lines)
    assert "winner_input=0 winner_key=C:/:Music/:one.mp3" in lines[0]
    assert "base" not in lines[0].split("winner_input=")[1]


def test_a_run_the_rule_settled_nothing_for_prints_no_outlier_line(tmp_path: Path) -> None:
    """A header with nothing under it reads as a run that lost something,
    so a run with no settled group prints no line at all.

    Fail-first mutation: _print_settled_outliers printed
    "settled_outliers:" before its loop, unconditionally.
    Observed:
        E       AssertionError: assert ['settled_outliers:'] == []
        E
        E         Left contains one more item: 'settled_outliers:'
        E         Use -v to get more diff
    """
    base, source, out = _identical_pair(tmp_path)
    result = _splice(tmp_path, base, out, source)
    assert result.exit_code == 0
    assert [line for line in result.stdout.splitlines() if "settled_outlier" in line] == []
    assert "groups_settled_by_rule=0" in result.stdout


def test_a_run_with_a_conflict_and_a_settled_group_prints_both(tmp_path: Path) -> None:
    """One group put to the operator and one answered by the rule report
    side by side, and --conflict-report writes the same header and the
    same single row it writes for a run with no settled group at all.

    Fail-first mutation: splice.py's tier branch taken whenever a group
    diverges on any measured attribute, its editorial names ignored, so
    the ARTIST group settled instead of conflicting.
    Observed:
        E       AssertionError: assert 'conflicts_reported=1' in 'inputs_merged=1\nidentity_groups=2\nconflicts_reported=0\ngroups_settled_by_rule=2\nsettled_groups_outlying=1\ncollec..._written=C:/Users/marcu/AppData/Local/Temp/pytest-of-marcu/pytest-1525/test_a_run_with_a_conflict_and0/mixed_out.nml'
    """
    base, source, out, report = _mixed_pair(tmp_path)
    result = _splice(
        tmp_path, base, out, source,
        "--on-conflict", "keep-first", "--conflict-report", str(report),
    )
    assert result.exit_code == 0
    assert "conflicts_reported=1" in result.stdout
    assert "groups_settled_by_rule=1" in result.stdout
    rows = report.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "identity_key,attrs,resolution"
    assert len(rows) == 2


def test_conflict_report_pointing_at_a_missing_parent_still_exits_two(tmp_path: Path) -> None:
    """The exit-code-2-on-write-failure contract is untouched by the
    settled listing printed above it, and the listing is printed before
    the refusal rather than lost with it.

    Fail-first mutation: the _print_settled_outliers call moved below the
    _write_conflict_report return.
    Observed:
        E       assert 0 == 1
        E        +  where 0 = len([])
    """
    base, source, out, _ = _mixed_pair(tmp_path)
    missing = tmp_path / "nowhere" / "conflicts.csv"
    result = _splice(
        tmp_path, base, out, source,
        "--on-conflict", "keep-first", "--conflict-report", str(missing),
    )
    assert result.exit_code == 2
    settled = [line for line in result.stdout.splitlines() if line.startswith("settled_outlier ")]
    assert len(settled) == 1
