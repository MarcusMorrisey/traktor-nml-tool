"""Split: playlist-scoped partition, dangling reference policy, byte fidelity."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import run_tool


def _nml(entries_xml: str, entries_count: int, playlists_xml: str, playlist_count: int, sorting_info_xml: str = "") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
        f'<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="{playlist_count}">'
        f"{playlists_xml}</SUBNODES></NODE></PLAYLISTS>"
        f"<SETS></SETS><INDEXING>{sorting_info_xml}</INDEXING></NML>"
    )


def _entry(artist, title, filename, size="16"):
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="/:Music/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
        f'<INFO BITRATE="320" PLAYTIME_FLOAT="1.0" FILESIZE="{size}"></INFO>'
        "</ENTRY>"
    )


def _playlist(name: str, keys: list[str], uuid: str) -> str:
    entries = "".join(f'<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="{k}"></PRIMARYKEY></ENTRY>' for k in keys)
    return (
        f'<NODE TYPE="PLAYLIST" NAME="{name}">'
        f'<PLAYLIST ENTRIES="{len(keys)}" TYPE="LIST" UUID="{uuid}">{entries}</PLAYLIST>'
        "</NODE>"
    )


def _key(filename: str) -> str:
    """Compute the flattened VOLUME+DIR+FILE PRIMARYKEY these fixtures'
    playlists reference, matching the schema's own KEY derivation
    exactly."""
    return "C:" + "/:Music/:" + filename


def test_split_by_playlist_keeps_only_selected_entries(tmp_path: Path) -> None:
    src = tmp_path / "src.nml"
    src.write_text(
        _nml(
            _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3"),
            2,
            _playlist("Keep", [_key("one.mp3")], "uuid-keep") + _playlist("Other", [_key("two.mp3")], "uuid-other"),
            2,
        ),
        encoding="utf-8", newline="",
    )
    out = tmp_path / "out.nml"
    result = run_tool(["split", str(src), "--group", str(out), "Keep"], cwd=tmp_path)
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "one.mp3" in text
    assert "two.mp3" not in text
    assert 'ENTRIES="1"' in text.split("COLLECTION")[1][:40]


def test_playlist_named_in_no_group_is_reported_and_excluded(tmp_path: Path) -> None:
    # "Skip" exists in the source but is not named in any --group: it must
    # appear in no output, and a --group name that matches no playlist at
    # all ("DoesNotExist") must be reported via playlists_unknown rather
    # than silently ignored.
    src = tmp_path / "src.nml"
    src.write_text(
        _nml(
            _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3"),
            2,
            _playlist("Keep", [_key("one.mp3")], "uuid-keep") + _playlist("Skip", [_key("two.mp3")], "uuid-skip"),
            2,
        ),
        encoding="utf-8", newline="",
    )
    out = tmp_path / "out.nml"
    result = run_tool(["split", str(src), "--group", str(out), "Keep,DoesNotExist"], cwd=tmp_path)
    assert result.exit_code == 0
    assert "playlists_unknown=['DoesNotExist']" in result.stdout
    text = out.read_text(encoding="utf-8")
    assert "Keep" in text
    assert "Skip" not in text
    assert "uuid-skip" not in text
    assert "DoesNotExist" not in text


def test_dangling_reference_excluded_by_default(tmp_path: Path) -> None:
    # "Mixed" references a track with no matching COLLECTION entry at all
    # (already broken in the source) - that reference is outside anything
    # this output's COLLECTION can ever contain, so it must be dropped by
    # default rather than left dangling in the output.
    src = tmp_path / "src.nml"
    src.write_text(
        _nml(
            _entry("A", "One", "one.mp3"),
            1,
            _playlist("Mixed", [_key("one.mp3"), _key("ghost.mp3")], "uuid-mixed"),
            1,
        ),
        encoding="utf-8", newline="",
    )
    out = tmp_path / "out.nml"
    result = run_tool(["split", str(src), "--group", str(out), "Mixed"], cwd=tmp_path)
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "ghost.mp3" not in text
    assert "one.mp3" in text


def test_dangling_reference_fails_under_fail_policy(tmp_path: Path) -> None:
    src = tmp_path / "src.nml"
    src.write_text(
        _nml(
            _entry("A", "One", "one.mp3"),
            1,
            _playlist("Mixed", [_key("one.mp3"), _key("ghost.mp3")], "uuid-mixed"),
            1,
        ),
        encoding="utf-8", newline="",
    )
    out = tmp_path / "out.nml"
    result = run_tool(
        ["split", str(src), "--group", str(out), "Mixed", "--dangling-policy", "fail"], cwd=tmp_path
    )
    assert result.exit_code == 2
    assert not out.exists()


def test_no_output_written_when_second_group_fails(tmp_path: Path) -> None:
    # The second group's own requested playlist ("Mixed") holds a
    # genuinely dangling reference (ghost.mp3 has no matching COLLECTION
    # entry at all), which --dangling-policy fail reports as an error for
    # that group - distinct from an unrelated playlist elsewhere in the
    # document holding a broken reference, which (DL-020) must never
    # affect a group that did not request it.
    src = tmp_path / "src.nml"
    src.write_text(
        _nml(
            _entry("A", "One", "one.mp3"),
            1,
            _playlist("Keep", [_key("one.mp3")], "uuid-keep")
            + _playlist("Mixed", [_key("one.mp3"), _key("ghost.mp3")], "uuid-mixed"),
            2,
        ),
        encoding="utf-8", newline="",
    )
    out1 = tmp_path / "out1.nml"
    out2 = tmp_path / "out2.nml"
    result = run_tool(
        [
            "split", str(src),
            "--group", str(out1), "Keep",
            "--group", str(out2), "Mixed",
            "--dangling-policy", "fail",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 2
    assert not out1.exists()
    assert not out2.exists()


def test_omitted_playlist_sorting_info_is_dropped_and_reported(tmp_path: Path) -> None:
    src = tmp_path / "src.nml"
    src.write_text(
        _nml(
            _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3"),
            2,
            _playlist("Keep", [_key("one.mp3")], "uuid-keep") + _playlist("Skip", [_key("two.mp3")], "uuid-skip"),
            2,
            sorting_info_xml=(
                '<SORTING_INFO PATH="Keep"></SORTING_INFO>'
                '<SORTING_INFO PATH="Skip"><CRITERIA ATTRIBUTE="7" DIRECTION="0"></CRITERIA></SORTING_INFO>'
            ),
        ),
        encoding="utf-8", newline="",
    )
    out = tmp_path / "out.nml"
    result = run_tool(["split", str(src), "--group", str(out), "Keep"], cwd=tmp_path)
    assert result.exit_code == 0
    assert "sorting_info_dropped=['Skip']" in result.stdout
    text = out.read_text(encoding="utf-8")
    assert 'PATH="Keep"' in text
    assert 'PATH="Skip"' not in text


def test_group_succeeds_under_fail_policy_despite_broken_reference_in_unrequested_playlist(
    tmp_path: Path,
) -> None:
    """An unrequested playlist elsewhere in the same file holding a broken
    reference must not affect this group's outcome: the dangling policy is
    scoped to only the group's own resolved playlists."""
    src = tmp_path / "src.nml"
    src.write_text(
        _nml(
            _entry("A", "One", "one.mp3"),
            1,
            _playlist("Keep", [_key("one.mp3")], "uuid-keep")
            + _playlist("Unrelated", [_key("one.mp3"), _key("ghost.mp3")], "uuid-unrelated"),
            2,
        ),
        encoding="utf-8", newline="",
    )
    out = tmp_path / "out.nml"
    result = run_tool(
        ["split", str(src), "--group", str(out), "Keep", "--dangling-policy", "fail"], cwd=tmp_path
    )
    assert result.exit_code == 0
    assert out.exists()


def test_pull_in_adds_no_track_only_referenced_by_an_unrequested_playlist(tmp_path: Path) -> None:
    src = tmp_path / "src.nml"
    src.write_text(
        _nml(
            _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3"),
            2,
            _playlist("Keep", [_key("one.mp3")], "uuid-keep")
            + _playlist("Unrelated", [_key("one.mp3"), _key("two.mp3")], "uuid-unrelated"),
            2,
        ),
        encoding="utf-8", newline="",
    )
    out = tmp_path / "out.nml"
    result = run_tool(
        ["split", str(src), "--group", str(out), "Keep", "--dangling-policy", "pull-in"], cwd=tmp_path
    )
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "one.mp3" in text
    # "Unrelated" is not requested, so its reference to two.mp3 must never
    # pull two.mp3 into this group's output.
    assert "two.mp3" not in text
