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
