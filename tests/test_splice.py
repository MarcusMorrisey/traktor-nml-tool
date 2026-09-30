"""Splice: playlist merge, name collision, and conflict abort/report."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from traktor_nml.confidence import MatchConfidence
from traktor_nml.model import collection_records
from traktor_nml.splice import (
    _TRACKED_ATTRS,
    _apply_replacements,
    _resolve_conflicts,
    assemble_output,
    group_identities,
)
from traktor_nml.xmlio import parse_xml_bytes
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


def _diverged(bitrate: str) -> tuple:
    """The pair of str.replace arguments that moves one copy of an _entry
    away from base, applied as `text.replace(*_diverged("128"))`.

    It moves BITRATE and gives the copy an ALBUM of its own in one
    substitution, because the two are one divergence. A group diverging on
    measured attributes alone is settled by rule and reports no conflict row
    (DL-325), so every fixture that is about conflict behaviour - the abort,
    the resolution, the candidates, the CSV report - needs an editorial name
    to be a conflict at all, and the measured name rides along in attrs
    exactly as DL-327 says it does.

    The ALBUM child is written after </LOCATION>, which is the child order
    textpatch writes in, and base's own copy carries no ALBUM child at all -
    the empty album string a record with no ALBUM element reads as."""
    return (
        '</LOCATION><INFO BITRATE="320"',
        '</LOCATION><ALBUM TITLE="Alb %s"></ALBUM><INFO BITRATE="%s"' % (bitrate, bitrate),
    )


# The editorial half of a divergence that inserts no child element. ARTIST
# stands on the ENTRY tag base already carries, so a patch naming the source
# substitutes a value inside base's own span rather than writing a new child
# into it - which is what a guard reading the bytes a substitution leaves,
# or the children base's entry keeps, needs its divergence to be (DL-327).
_DIVERGED_ARTIST = ('ARTIST="A"', 'ARTIST="A2"')


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
        _nml(_entry("A", "Song", "track.mp3", time="100.0").replace(*_diverged("128")), 1, ""),
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
        _nml(_entry("A", "Song", "track.mp3", time="100.0").replace(*_diverged("128")), 1, ""),
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


def _parsed(text: str) -> tuple:
    """A (source text, parsed root) contribution pair, the shape
    assemble_output takes for base and for every contribution alike."""
    return text, parse_xml_bytes(text.encode("utf-8"))


def _diverging_pair() -> tuple:
    """A base collection and one source collection holding the same track
    with a differing ALBUM and BITRATE - the smallest input reaching the
    conflict branch, and the shape the CLI conflict guards build. The
    editorial name is what a conflict is raised for; a divergence over the
    measured names alone is settled by rule and reports no row to decide
    (DL-325, DL-327).
    Returned as parsed roots so a guard calls assemble_output directly:
    resolutions has no CLI flag to drive it through run_tool (DL-108)."""
    base_text = _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, "")
    source_text = _nml(
        _entry("A", "Song", "track.mp3", time="100.0").replace(*_diverged("128")), 1, ""
    )
    return base_text, parse_xml_bytes(base_text.encode("utf-8")), [_parsed(source_text)]


def _pair_naming(row, input_idx: int) -> tuple:
    """The (input index, primary key) pair naming the record input_idx
    contributes to a reported row's group, read off the row's own
    candidates so no guard reconstructs a primary key of its own. The
    primary key is derived from the location (DL-004), so this pair, not
    the key alone, is what tells two inputs' copies of one file apart."""
    for candidate in row.candidates:
        for pair in candidate.members:
            if pair[0] == input_idx:
                return pair
    raise AssertionError("no member from input %d in %r" % (input_idx, row.candidates))


def _reported(base_text: str, base_root, contributions):
    """The row a run over these inputs reports on the abort path, which is
    where a guard reads a group's identity key and its candidates from."""
    return assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT
    ).conflict_rows[0]


def test_an_empty_resolutions_mapping_reproduces_the_omitted_parameter_bytes() -> None:
    """An empty mapping settles nothing, which is what the parameter's
    absence settles, so the two runs agree byte for byte over one input.

    Observed with assemble_output's resolutions default changed from None
    to {"C:/:Music/:track.mp3": (1, "C:/:Music/:track.mp3")}, so the
    omitted-parameter call settled the group differently from the
    empty-mapping call: AssertionError on `assert empty.output ==
    omitted.output`, the diff reading `- BITRATE="128"` against
    `+ BITRATE="320"` - the omitted run took the pick the default carried.
    """
    base_text, base_root, contributions = _diverging_pair()
    omitted = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT, "keep-first"
    )
    empty = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT, "keep-first", resolutions={}
    )
    assert empty.output is not None
    assert empty.output == omitted.output
    assert empty.output.encode("utf-8") == omitted.output.encode("utf-8")


def test_a_pair_naming_the_base_record_writes_the_base_records_attributes() -> None:
    """A pair naming the group's base-input record leaves base's own values
    standing, so the merged collection carries base's BITRATE and the
    source's is nowhere in the output (DL-007, DL-116).

    Observed with the base branch's `if picked is not None and picked[1]
    is not winner:` and its `_, named_record = picked` replaced by `if
    picked is not None:` and `_, named_record = pick_non_base()`, so a
    pick took its values from the run-wide picker rather than from the
    pair: AssertionError on `assert 'BITRATE="320"' in result.output`,
    base's entry rewritten to the source's BITRATE="128".
    """
    base_text, base_root, contributions = _diverging_pair()
    row = _reported(base_text, base_root, contributions)
    result = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT,
        resolutions={row.identity_key: _pair_naming(row, 0)},
    )
    assert result.output is not None
    assert 'BITRATE="320"' in result.output
    assert 'BITRATE="128"' not in result.output
    assert _entry_count(result.output) == 1
    assert result.conflict_rows[0].resolution == "0:" + row.identity_key


def test_a_pair_naming_the_source_record_writes_that_records_attributes() -> None:
    """The pair names which record supplies the values patched into base's
    own ENTRY, so the named copy's BITRATE reaches the output, base's value
    is absent from it, and the collection still holds exactly one entry for
    that LOCATION (DL-004, DL-116).

    Observed with the base branch's entry_patches.append(...) replaced by
    `new_entries.append((picked[0], named_record))`, transplanting the
    named record's ENTRY beside base's instead of patching base's:
    AssertionError on `assert 'BITRATE="320"' not in result.output`, the
    COLLECTION holding base's entry at BITRATE="320" beside a second one
    at BITRATE="128" over the same LOCATION.
    """
    base_text, base_root, contributions = _diverging_pair()
    row = _reported(base_text, base_root, contributions)
    result = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT,
        resolutions={row.identity_key: _pair_naming(row, 1)},
    )
    assert result.output is not None
    assert 'BITRATE="128"' in result.output
    assert 'BITRATE="320"' not in result.output
    assert _entry_count(result.output) == 1
    assert _files(result.output).count("track.mp3") == 1
    assert result.conflict_rows[0].resolution == "1:" + row.identity_key


def test_one_primary_key_and_two_members_are_told_apart_by_the_input_index() -> None:
    """base and a source at the identical path put two records in one group
    under a single primary key, since the key is derived from the location
    (DL-004): the group's member_keys holds one key while its candidates
    name two contributors, and the two pairs over that one key settle the
    group two different ways (DL-148).

    Observed with the member match `(idx, record.primary_key) == pair`
    replaced by `record.primary_key == pair[1]`, dropping the input index
    from the comparison: AssertionError on `assert picked[0] !=
    picked[1]`, the two runs producing the identical output because both
    pairs matched base's record first.
    """
    base_text, base_root, contributions = _diverging_pair()
    row = _reported(base_text, base_root, contributions)
    contributors = [pair for candidate in row.candidates for pair in candidate.members]
    assert len(row.member_keys) == 1
    assert len(contributors) == 2
    assert {idx for idx, _ in contributors} == {0, 1}
    assert {key for _, key in contributors} == set(row.member_keys)

    picked = {
        idx: assemble_output(
            base_text, base_root, contributions, MatchConfidence.STRICT,
            resolutions={row.identity_key: _pair_naming(row, idx)},
        ).output
        for idx in (0, 1)
    }
    assert picked[0] != picked[1]
    assert 'BITRATE="320"' in picked[0] and 'BITRATE="128"' not in picked[0]
    assert 'BITRATE="128"' in picked[1] and 'BITRATE="320"' not in picked[1]


def test_an_unmatched_resolutions_key_is_inert() -> None:
    """A key naming no identity group is absent from the lookup, so the run
    is the run it is with an empty mapping - here, the DL-008 abort.

    Observed with the lookup written as `resolutions[identity_key] if
    divergent_attrs else None` in place of `resolutions.get(identity_key)
    if divergent_attrs else None`: KeyError: 'C:/:Music/:track.mp3' raised
    at traktor_nml/splice.py:176.
    """
    base_text, base_root, contributions = _diverging_pair()
    result = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT,
        resolutions={"C:" + "/:Music/:" + "nothing.mp3": (0, "C:" + "/:Music/:" + "nothing.mp3")},
    )
    assert result.output is None
    assert result.errors == ["unresolved_conflicts"]


def _three_way_bitrate() -> tuple:
    """base and two sources holding one track, disagreeing on ALBUM, on
    FILESIZE and three ways on BITRATE. The two sources differ from each
    other, so input 2 is a value neither base nor the keep-first non-base
    copy carries: a guard naming input 2 cannot pass by coincidence with the
    run-wide picker.

    ALBUM is what makes the group a conflict at all: a divergence over the
    measured attributes alone is settled by rule and reports no conflict row
    (DL-325). base carries no ALBUM child, so its album value is the empty
    string, and the three answers are three distinct tuples."""
    base_text = _nml(_entry("A", "Song", "track.mp3", size="16", time="100.0"), 1, "")
    first = _nml(
        _entry("A", "Song", "track.mp3", size="32", time="100.0").replace(*_diverged("128")), 1, "",
    )
    second = _nml(
        _entry("A", "Song", "track.mp3", size="32", time="100.0").replace(*_diverged("064")), 1, "",
    )
    return base_text, parse_xml_bytes(base_text.encode("utf-8")), [_parsed(first), _parsed(second)]


def test_a_conflict_row_carries_one_candidate_per_distinct_answer() -> None:
    """A row's candidates hold one entry per distinct tuple of divergent
    values, each tuple lining up with attrs position by position and each
    candidate naming the (input index, primary key) pairs that supply it,
    sorted by input index (DL-149, DL-150).

    Mutation: _candidates was changed to read `for attr in
    reversed(attrs)` and this guard rerun. Observed:
        AssertionError: assert {('064', '32'...track.mp3'),)} == {('', '16', '...track.mp3'),)}

          Left contains 3 more items:
          {('064', '32', 'Alb 064'): ((2, 'C:/:Music/:track.mp3'),),
           ('128', '32', 'Alb 128'): ((1, 'C:/:Music/:track.mp3'),),
           ('320', '16', ''): ((0, 'C:/:Music/:track.mp3'),)}
          Right contains 3 more items:
          {('', '16', '320'): ((0, 'C:/:Music/:track.mp3'),),...

          ...Full output truncated (3 lines hidden), use '-vv' to show
    """
    base_text, base_root, contributions = _three_way_bitrate()
    result = assemble_output(base_text, base_root, contributions, MatchConfidence.STRICT)

    row = result.conflict_rows[0]
    key = "C:" + "/:Music/:" + "track.mp3"
    assert row.attrs == "album,filesize,bitrate"
    assert len(row.candidates) == 3
    assert all(len(c.values) == len(row.attrs.split(",")) for c in row.candidates)
    # Position 0 is ALBUM, 1 is FILESIZE and 2 is BITRATE, in every
    # candidate: the order attrs names, which is _TRACKED_ATTRS' own.
    assert {c.values: c.members for c in row.candidates} == {
        ("", "16", "320"): ((0, key),),
        ("Alb 128", "32", "128"): ((1, key),),
        ("Alb 064", "32", "064"): ((2, key),),
    }


def test_records_agreeing_on_every_divergent_attribute_are_one_candidate() -> None:
    """Candidates are keyed by their tuple of divergent values, so two
    sources that agree collapse into one candidate naming both contributors
    rather than into two identical answers (DL-150).

    Mutation: the candidate key in _candidates was written as `values +
    (str(input_idx),)`, so each record kept its own entry, and this guard
    rerun. Observed:
        AssertionError: assert 3 == 2
         +  where 3 = len((ConflictCandidate(values=('', '320', '0'), members=((0, 'C:/:Music/:track.mp3'),)), ConflictCandidate(values=('Alb 12... 'C:/:Music/:track.mp3'),)), ConflictCandidate(values=('Alb 128', '128', '2'), members=((2, 'C:/:Music/:track.mp3'),))))
         +    where (ConflictCandidate(values=('', '320', '0'), members=((0, 'C:/:Music/:track.mp3'),)), ConflictCandidate(values=('Alb 12... 'C:/:Music/:track.mp3'),)), ConflictCandidate(values=('Alb 128', '128', '2'), members=((2, 'C:/:Music/:track.mp3'),))) = ConflictRow(identity_key='C:/:Music/:track.mp3', attrs='album,bitrate', resolution='unresolved', member_keys=frozenset.../:Music/:track.mp3'),))), agreed=(('artist', 'A'), ('title', 'Song'), ('filesize', '16'), ('playtime_float', '100.0'))).candidates
    """
    base_text = _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, "")
    agreeing = _nml(
        _entry("A", "Song", "track.mp3", time="100.0").replace(*_diverged("128")),
        1, "",
    )
    result = assemble_output(
        base_text, parse_xml_bytes(base_text.encode("utf-8")),
        [_parsed(agreeing), _parsed(agreeing)], MatchConfidence.STRICT,
    )

    row = result.conflict_rows[0]
    key = "C:" + "/:Music/:" + "track.mp3"
    assert row.attrs == "album,bitrate"
    assert len(row.candidates) == 2
    assert {c.values: c.members for c in row.candidates} == {
        ("", "320"): ((0, key),),
        ("Alb 128", "128"): ((1, key), (2, key)),
    }


# The agreeing values are a field beside attrs, not a widening of it
# (ref: DL-244), and they are well defined because an attribute outside
# the divergent set holds one value across every member of the group
# (ref: DL-245). The three-answer group is what proves the second
# reading rather than assuming it; the CSV guard is what holds the first
# where a fold into attrs would otherwise pass unseen (ref: DL-189).


def _deep_entry(artist, title, album, size, time, bitrate) -> str:
    """An ENTRY three folders deep carrying every tracked attribute as a
    caller-set value, so two of these can disagree on all six and still
    group: the path_suffix_3 tier strict admits reads the location alone
    and needs three folder levels to fire."""
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="/:Music/:Sets/:Deep/:" FILE="one.mp3" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
        f'<ALBUM TITLE="{album}"></ALBUM>'
        f'<INFO BITRATE="{bitrate}" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
        "</ENTRY>"
    )


def test_a_three_answer_group_carries_the_agreeing_tracked_attributes() -> None:
    """A metadata-diverging group reports the tracked attributes it
    agrees on as (name, value) pairs in _TRACKED_ATTRS order, each
    holding the single value every member carries.

    Read against a group of three answers so the reading is not
    satisfied by a two-member group where every tracked attribute is
    either divergent or identical by coincidence.

    Mutation: `if attr not in divergent` in splice._agreed was changed
    to `if attr in divergent` and this guard rerun. Observed:
        AssertionError: assert (('album', ''...rate', '320')) == (('artist', '...at', '100.0'))

          At index 0 diff: ('album', '') != ('artist', 'A')
          Right contains 2 more items, first extra item: ('filesize', '8192')
          Use -v to get more diff
    """
    base_text = _nml(_entry("A", "One", "one.mp3", size="8192", time="100.0"), 1, "")
    first = base_text.replace(*_diverged("128"))
    second = base_text.replace(*_diverged("064"))
    result = assemble_output(
        base_text, parse_xml_bytes(base_text.encode("utf-8")),
        [_parsed(first), _parsed(second)], MatchConfidence.STRICT,
    )

    row = result.conflict_rows[0]
    assert len(row.candidates) == 3
    assert row.attrs == "album,bitrate"
    assert row.agreed == (
        ("artist", "A"),
        ("title", "One"),
        ("filesize", "8192"),
        ("playtime_float", "100.0"),
    )


def test_a_group_diverging_on_every_tracked_attribute_carries_no_agreed_pairs() -> None:
    """agreed is the complement of attrs, so a group that agrees on
    nothing carries none - the empty tuple rather than a pair holding an
    arbitrary member's value.

    Mutation: `divergent = set(attrs)` in splice._agreed was changed to
    `divergent = set()` and this guard rerun. Observed:
        AssertionError: assert (('artist', '...rate', '320')) == ()
          Left contains 6 more items, first extra item: ('artist', 'A')
    """
    base_text = _nml(_deep_entry("A", "One", "Alb", "16", "100.0", "320"), 1, "")
    source_text = _nml(_deep_entry("B", "Two", "Bee", "32", "200.0", "128"), 1, "")
    result = assemble_output(
        base_text, parse_xml_bytes(base_text.encode("utf-8")),
        [_parsed(source_text)], MatchConfidence.STRICT,
    )

    row = result.conflict_rows[0]
    assert set(row.attrs.split(",")) == set(_TRACKED_ATTRS)
    assert row.agreed == ()


def test_the_conflict_report_and_the_printed_line_are_unmoved_by_agreed(tmp_path: Path) -> None:
    """The CSV conflict report's columns and splice_cmd's printed line
    read identically over a run whose rows carry agreed pairs: agreed is
    a field the report never reads, and attrs is still the comma-joined
    divergent set.

    This is the reading that stays true in the broken state where agreed
    was folded into attrs - the shape that would make the third CSV
    column name fields the group agreed on (DL-189).

    Mutation: `",".join(divergent_attrs)` in _metadata_conflict_row was
    changed to `",".join(divergent_attrs + [a for a, _ in _agreed(members, divergent_attrs)])`
    and this guard rerun. Observed:
        assert ['identity_ke...",keep-first'] == ['identity_ke...",keep-first']

          At index 1 diff: 'C:/:Music/:one.mp3,"album,bitrate,artist,title,filesize,playtime_float",keep-first' != 'C:/:Music/:one.mp3,"album,bitrate",keep-first'
          Use -v to get more diff
    """
    base_text = _nml(_entry("A", "One", "one.mp3", size="8192", time="100.0"), 1, "")
    source_text = base_text.replace(*_diverged("128"))
    base_path = tmp_path / "base.nml"
    base_path.write_text(base_text, encoding="utf-8", newline="")
    other_path = tmp_path / "other.nml"
    other_path.write_text(source_text, encoding="utf-8", newline="")
    csv_path = tmp_path / "conflicts.csv"

    # The same inputs through the library call, so the guard reads for
    # itself that the run whose report it pins carries agreeing values.
    carried = assemble_output(
        base_text, parse_xml_bytes(base_text.encode("utf-8")),
        [_parsed(source_text)], MatchConfidence.STRICT, on_conflict="keep-first",
    ).conflict_rows[0]
    assert carried.agreed != ()

    result = run_tool(
        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path),
         "--on-conflict", "keep-first", "--conflict-report", str(csv_path)],
        cwd=tmp_path,
    )

    assert result.exit_code == 0
    assert csv_path.read_text(encoding="utf-8", newline="").splitlines() == [
        "identity_key,attrs,resolution",
        "C:" + "/:Music/:" + 'one.mp3,"album,bitrate",keep-first',
    ]
    assert (
        "conflict_key=C:" + "/:Music/:" + "one.mp3 attrs=album,bitrate resolution=keep-first"
    ) in result.stdout.splitlines()


def test_a_duplicate_playlist_name_row_and_an_ambiguous_redirect_row_keep_their_shape() -> None:
    """The two rows built from a literal name no identity group, and
    carry agreed empty rather than a pair read off members they do not
    have.

    Mutation: ConflictRow.agreed's default was changed from `()` to
    `(("artist", ""),)` and this guard rerun. Observed:
        AssertionError: assert (('artist', ''),) == ()
          Left contains one more item: ('artist', '')
    """
    track_key = "C:" + "/:Music/:" + "track.mp3"
    entries = _entry("A", "Song", "track.mp3", time="100.0")
    duplicate_base = _nml(
        entries, 1,
        _playlist("MySet", [], "uuid-base") + _playlist("MySet", [track_key], "uuid-base2"),
    )
    duplicate_source = _nml(
        entries.replace(*_diverged("128")), 1,
        _playlist("MySet", [track_key], "uuid-prev"),
    )
    duplicate_result = _resolved(duplicate_base, duplicate_source, 1, reconstruct=True)
    name_row = next(
        row for row in duplicate_result.conflict_rows if row.attrs == "playlist_name"
    )

    a1 = _entry("A", "Song", "a1.mp3", time="100.0")
    a2 = _entry("A", "Song", "a2.mp3", time="100.0")
    a3 = _entry("A", "Song", "a3.mp3", time="100.0").replace(*_diverged("128"))
    other = _entry("B", "Other", "other.mp3")
    redirect_base = _nml(
        a1 + a2 + other, 3, _playlist("MySet", ["C:" + "/:Music/:" + "a1.mp3"], "uuid-base")
    )
    redirect_source = _nml(
        a3 + other, 2,
        _playlist(
            "MySet",
            ["C:" + "/:Music/:" + "other.mp3", "C:" + "/:Music/:" + "a3.mp3"],
            "uuid-prev",
        ),
    )
    redirect_result = _resolved(redirect_base, redirect_source, 1, reconstruct=True)
    redirect_row = next(
        row for row in redirect_result.conflict_rows if row.attrs == "ambiguous_redirect"
    )

    for row in (name_row, redirect_row):
        assert row.agreed == ()
        assert row.member_keys == frozenset()


def test_a_pick_naming_the_second_source_beats_the_keep_first_answer() -> None:
    """The pair names one record, so a pick on input 2 writes input 2's
    values while keep-first names input 1 and base's own values are what the
    run would otherwise keep: all three answers are distinct and only the
    named one reaches the output, which still holds one entry for the
    LOCATION (DL-004, DL-148, DL-151).

    Observed with the base branch's `_, named_record = picked` replaced by
    `_, named_record = pick_non_base()`, the run-wide picker answering in
    place of the pair: AssertionError on `assert 'BITRATE="064"' in
    result.output`, the patched entry reading `<INFO BITRATE="128"
    PLAYTIME_FLOAT="100.0" FILESIZE="32">` - keep-first's input 1, not
    the input 2 the pair named.
    """
    base_text, base_root, contributions = _three_way_bitrate()
    row = _reported(base_text, base_root, contributions)
    assert _pair_naming(row, 1) != _pair_naming(row, 2)

    result = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT, "keep-first",
        resolutions={row.identity_key: _pair_naming(row, 2)},
    )
    assert result.output is not None
    assert _entry_count(result.output) == 1
    assert _files(result.output).count("track.mp3") == 1
    assert 'BITRATE="064"' in result.output
    # keep-first names input 1, and base's own value is 320: neither survives.
    assert 'BITRATE="128"' not in result.output
    assert 'BITRATE="320"' not in result.output
    assert 'FILESIZE="32"' in result.output


def test_a_pair_naming_no_member_falls_through_to_on_conflict_or_aborts() -> None:
    """A pair naming no member of the group settles nothing, so the group is
    the group an omitted key leaves: settled by on_conflict where there is
    one, and aborting unresolved where there is not (DL-105, DL-153, DL-159).

    Observed with the member lookup's `next(..., None)` default replaced
    by `next(..., (0, members[0][1]))`, so a pair naming no member fell
    back to the group's first record: AssertionError `assert
    '0:C:/:Music/:track.mp3' == 'keep-first'` - the stale pair settled
    the group instead of leaving it to on_conflict.
    """
    base_text, base_root, contributions = _three_way_bitrate()
    row = _reported(base_text, base_root, contributions)
    stale = {row.identity_key: (5, "C:" + "/:Music/:" + "track.mp3")}

    settled = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT, "keep-first",
        resolutions=stale,
    )
    assert settled.output is not None
    assert settled.conflict_rows[0].resolution == "keep-first"
    # base keeps its own entry and no pick supplies values, so base's own
    # BITRATE stands and neither source's reaches the output.
    assert 'BITRATE="320"' in settled.output
    assert 'BITRATE="128"' not in settled.output
    assert 'BITRATE="064"' not in settled.output

    aborted = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT, resolutions=stale
    )
    assert aborted.output is None
    assert aborted.errors == ["unresolved_conflicts"]
    assert aborted.conflict_rows[0].resolution == "unresolved"


def _resolved_groups(base_text: str, contribution_texts: list, **kwargs):
    """_resolve_conflicts over these inputs, so a guard can read the parts
    of its result assemble_output does not surface - old_to_new_key, which
    is the redirect target the playlist PRIMARYKEY rewrite follows, and
    ambiguous_keys."""
    roots = [parse_xml_bytes(base_text.encode("utf-8"))] + [
        parse_xml_bytes(text.encode("utf-8")) for text in contribution_texts
    ]
    groups = group_identities(
        [collection_records(root) for root in roots], MatchConfidence.STRICT
    )
    return _resolve_conflicts(groups, kwargs.pop("on_conflict", None), **kwargs)


def _base_less_pair() -> tuple:
    """base holding an unrelated track and two sources holding one track
    between them at different filenames, diverging on BITRATE: an identity
    group carrying no base record, whose two members carry distinct primary
    keys so the redirect target the pick names is visible."""
    base_text = _nml(_entry("Z", "Other", "other.mp3"), 1, "")
    first = _nml(_entry("A", "Song", "one.mp3", time="100.0"), 1, "")
    second = _nml(
        _entry("A", "Song", "two.mp3", time="100.0").replace(*_diverged("128")),
        1, "",
    )
    return base_text, [first, second]


def test_a_base_less_group_honours_the_pair_for_values_and_redirect_target() -> None:
    """Where the group holds no base record the pair names the winner
    appended to new_entries, so the pick decides both the ENTRY transplanted
    and the old_to_new_key redirect target every other member follows; where
    no resolution names the group the run-wide picker still answers it
    (DL-151, DL-152).

    Observed with the transplant branch's `winner_idx, winner = picked if
    picked is not None else pick_non_base()` replaced by `winner_idx,
    winner = pick_non_base()`: AssertionError on the redirect mapping,
    `Left contains 1 more item: {'C:/:Music/:two.mp3':
    'C:/:Music/:one.mp3'}` against the right's {'C:/:Music/:one.mp3':
    'C:/:Music/:two.mp3'} - the redirect ran to keep-first's input 1
    rather than to the input 2 the pair named.
    """
    base_text, contribution_texts = _base_less_pair()
    base_root = parse_xml_bytes(base_text.encode("utf-8"))
    contributions = [_parsed(text) for text in contribution_texts]
    row = _reported(base_text, base_root, contributions)
    first_key = "C:" + "/:Music/:" + "one.mp3"
    second_key = "C:" + "/:Music/:" + "two.mp3"
    assert _pair_naming(row, 1) == (1, first_key)
    assert _pair_naming(row, 2) == (2, second_key)

    named = {row.identity_key: _pair_naming(row, 2)}
    picked_redirects, _rows, _unresolved, picked_entries, _ambiguous = _resolved_groups(
        base_text, contribution_texts, resolutions=named
    )
    # keep-first names input 1, so a redirect running the other way is the
    # picker's answer rather than the operator's.
    assert picked_redirects == {first_key: second_key}
    assert [idx for idx, _ in picked_entries] == [2]

    fallback_redirects, _rows, _unresolved, fallback_entries, _ambiguous = _resolved_groups(
        base_text, contribution_texts, on_conflict="keep-first"
    )
    assert fallback_redirects == {second_key: first_key}
    assert [idx for idx, _ in fallback_entries] == [1]

    merged = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT, "keep-first",
        resolutions=named,
    )
    assert merged.output is not None
    assert _entry_count(merged.output) == 2
    assert _files(merged.output) == ["other.mp3", "two.mp3"]
    assert 'BITRATE="128"' in _collection_of(merged.output)


def test_a_multi_base_group_under_a_non_base_pick_keeps_every_key_ambiguous() -> None:
    """A group holding several base records has no single right redirect
    target whatever the pick, so every non-base primary key in it stays in
    ambiguous_keys and the reconstruction path still refuses the group
    (DL-094, DL-122, DL-151).

    Observed with the ambiguity guard read as `if len(base_members) > 1
    and picked is None:`, letting a pick excuse the group: AssertionError
    `assert set() == {'C:/:Music/:a3.mp3'}`, the mutated run reporting an
    empty ambiguous_keys, which is the set the reconstruction path reads
    before it refuses.
    """
    a1 = _entry("A", "Song", "a1.mp3", time="100.0")
    a2 = _entry("A", "Song", "a2.mp3", time="100.0")
    a3 = _entry("A", "Song", "a3.mp3", time="100.0").replace(*_diverged("128"))
    base_text = _nml(a1 + a2, 2, "")
    source_text = _nml(a3, 1, "")
    row = _reported(
        base_text, parse_xml_bytes(base_text.encode("utf-8")), [_parsed(source_text)]
    )

    resolved = _resolved_groups(
        base_text, [source_text], resolutions={row.identity_key: _pair_naming(row, 1)}
    )
    _redirects, _rows, _unresolved, new_entries, ambiguous_keys = resolved
    assert ambiguous_keys == {"C:" + "/:Music/:" + "a3.mp3"}
    assert new_entries == []
    assert [record.primary_key for record, _ in resolved.entry_patches] == [
        "C:" + "/:Music/:" + "a1.mp3"
    ]


def test_a_per_key_entry_governs_its_own_group_over_on_conflict() -> None:
    """The mapping is consulted first and on_conflict governs what the
    mapping does not name, so a named group follows its own pick while
    keep-last is in force for the rest of the run.

    Observed with the recorded resolution written as
    `_metadata_conflict_row(identity_key, divergent_attrs, members,
    on_conflict or resolution)`, letting the run-wide policy label a
    group the mapping decided: AssertionError `assert 'keep-last' ==
    '0:C:/:Music/:track.mp3'`.
    """
    base_text, base_root, contributions = _diverging_pair()
    row = _reported(base_text, base_root, contributions)
    result = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT, "keep-last",
        resolutions={row.identity_key: _pair_naming(row, 0)},
    )
    assert result.output is not None
    assert 'BITRATE="320"' in result.output
    assert 'BITRATE="128"' not in result.output
    assert result.conflict_rows[0].resolution == "0:" + row.identity_key


def test_a_mixed_run_resolves_the_named_group_and_aborts_on_the_unnamed_one() -> None:
    """One resolved group does not license a write while another group is
    undecided: the abort covers the run rather than the group, and it runs
    before any span is rewritten (DL-008).

    Observed with `unresolved = True` replaced by `unresolved = not
    resolutions`, so a run holding any resolution wrote its output:
    AssertionError - `assert '<?xml version="1.0" ... </NML>' is None`,
    the run's conflict_rows carrying the /:two.mp3 row at 'unresolved'.
    """
    base_text = _nml(
        _entry("A", "One", "one.mp3", time="100.0") + _entry("B", "Two", "two.mp3", time="200.0"), 2, ""
    )
    source_text = _nml(
        _entry("A", "One", "one.mp3", time="100.0").replace(*_diverged("128"))
        + _entry("B", "Two", "two.mp3", time="200.0").replace(*_diverged("192")),
        2, "",
    )
    base_root = parse_xml_bytes(base_text.encode("utf-8"))
    contributions = [_parsed(source_text)]
    named = "C:" + "/:Music/:" + "one.mp3"

    result = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT,
        resolutions={named: (0, named)},
    )
    assert result.output is None
    assert result.errors == ["unresolved_conflicts"]
    assert len(result.conflict_rows) == 2
    by_key = {row.identity_key: row.resolution for row in result.conflict_rows}
    assert by_key[named] == "0:" + named
    assert by_key["C:" + "/:Music/:" + "two.mp3"] == "unresolved"


def test_conflict_rows_are_populated_on_the_abort_path_and_the_clean_path() -> None:
    """conflict_rows carries one row per divergent group whatever the
    outcome, so the report the operator reads does not depend on whether the
    run wrote anything (DL-008).

    Observed with the clean path's `if divergent_attrs:` guarding its
    conflict_rows.append(...) replaced by `if False:`: AssertionError on
    `assert len(resolved.conflict_rows) == 1` - assert 0 == 1, where
    0 = len([]).
    """
    base_text, base_root, contributions = _diverging_pair()
    aborted = assemble_output(base_text, base_root, contributions, MatchConfidence.STRICT)
    row = aborted.conflict_rows[0]
    resolved = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT,
        resolutions={row.identity_key: _pair_naming(row, 0)},
    )
    assert len(aborted.conflict_rows) == 1
    assert len(resolved.conflict_rows) == 1
    assert aborted.conflict_rows[0].identity_key == resolved.conflict_rows[0].identity_key


def _two_source_divergence() -> tuple:
    """A base holding an unrelated track and two sources holding one track
    between them with differing BITRATEs: an identity group carrying no base
    record, which is the branch keying on the member primary keys."""
    base_text = _nml(_entry("Z", "Other", "other.mp3", time="9.0"), 1, "")
    first = _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, "")
    second = _nml(
        _entry("A", "Song", "track.mp3", time="100.0").replace(*_diverged("128")), 1, ""
    )
    return base_text, parse_xml_bytes(base_text.encode("utf-8")), first, second


def test_an_unchanged_groups_identity_key_survives_an_added_source() -> None:
    """The key is derived from the group's member records rather than from
    its union-find root index, so a source added ahead of the group's own
    members - which shifts every later record's index - leaves the group
    answering to the same name (DL-114).

    Observed with `identity_key = group_identity_key(members)` replaced by
    `identity_key = str(key)`, the union-find root index: the same group
    was named '1' in the two-input run and '2' in the three-input run, and
    the guard failed with AssertionError: assert '1' == '2'.
    """
    base_text, base_root, first, second = _two_source_divergence()
    filler = _nml(_entry("Q", "Filler", "filler.mp3", time="3.0"), 1, "")

    one = assemble_output(
        base_text, base_root, [_parsed(first), _parsed(second)], MatchConfidence.STRICT
    )
    two = assemble_output(
        base_text, base_root,
        [_parsed(filler), _parsed(first), _parsed(second)], MatchConfidence.STRICT,
    )
    one_source_key = one.conflict_rows[0].identity_key
    two_source_key = two.conflict_rows[0].identity_key
    assert one_source_key == two_source_key


def test_an_enlarged_group_carries_a_different_identity_key() -> None:
    """A group a further source enlarges is a different set of records and
    answers to a different name, so a pick made against the smaller group is
    not applied to the larger one (DL-114, DL-115).

    Observed with `identity_key = group_identity_key(members)` replaced by
    `identity_key = str(key)`, the union-find root index: both runs named
    the group '1', and the guard failed with AssertionError:
    assert '1' != '1'.
    """
    base_text, base_root, first, second = _two_source_divergence()
    third = _nml(
        _entry("A", "Song", "track.mp3", time="100.0").replace(*_diverged("192")), 1, ""
    )

    small = assemble_output(
        base_text, base_root, [_parsed(first), _parsed(second)], MatchConfidence.STRICT
    )
    enlarged = assemble_output(
        base_text, base_root,
        [_parsed(first), _parsed(second), _parsed(third)], MatchConfidence.STRICT,
    )
    small_key = small.conflict_rows[0].identity_key
    enlarged_key = enlarged.conflict_rows[0].identity_key
    assert small_key != enlarged_key


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


# --- a source pick over a track base already owns (DL-116..DL-124) -----------
#
# Every guard below reads a count or a structure a duplicate entry changes -
# the COLLECTION's ENTRY count and its ENTRIES attribute, the multiplicity of a
# LOCATION, a patched entry's child order, the counts of CRLF and of bare LF -
# rather than only a substring of the output, because a guard asserting the
# source's value is present passes while the collection holds two entries for
# one file (DL-126).


def _album_entry(artist, title, filename, album, size="16", time="1.0", bitrate="320"):
    """An ENTRY carrying an ALBUM child, written in the fixed child order
    LOCATION, ALBUM, INFO that Traktor writes and DL-127 anchors against."""
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="/:Music/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
        f'<ALBUM TITLE="{album}"></ALBUM>'
        f'<INFO BITRATE="{bitrate}" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
        "</ENTRY>"
    )


def _collection_of(text: str) -> str:
    return text[text.index("<COLLECTION"): text.index("</COLLECTION>")]


def _entry_count(text: str) -> int:
    return _collection_of(text).count("<ENTRY ")


def _entries_attr(text: str) -> str:
    return re.search(r'<COLLECTION ENTRIES="([^"]*)"', text).group(1)


def _files(text: str) -> list:
    return re.findall(r'<LOCATION[^>]*FILE="([^"]*)"', _collection_of(text))


def _child_tags(text: str, filename: str) -> list:
    """The child tag names of the COLLECTION entry whose LOCATION names
    filename, in document order."""
    collection = _collection_of(text)
    entries = re.findall(r"<ENTRY .*?</ENTRY>", collection, re.DOTALL)
    entry = next(e for e in entries if 'FILE="%s"' % filename in e)
    return re.findall(r"<([A-Z_]+)[\s/>]", entry)[1:]


def _resolved(base_text: str, source_text: str, input_idx: int, **kwargs):
    """Run assemble_output over one base and one contribution with the
    conflicting group settled by the pair naming input_idx's record, reading
    the group's identity key and that pair off the abort path so no guard
    carries its own copy of either derivation. Input 0 is base and input 1
    is the contribution."""
    row = _reported(
        base_text, parse_xml_bytes(base_text.encode("utf-8")), [_parsed(source_text)]
    )
    return assemble_output(
        base_text, parse_xml_bytes(base_text.encode("utf-8")), [_parsed(source_text)],
        MatchConfidence.STRICT,
        resolutions={row.identity_key: _pair_naming(row, input_idx)},
        **kwargs
    )


def _assembled(base_text: str, source_text: str):
    """assemble_output with reconstruct on over one base and one
    contribution that carry no divergence, so the run reaches its end
    with no resolution to supply - which is what a guard reading the
    stats of a completed run wants."""
    return assemble_output(
        base_text, parse_xml_bytes(base_text.encode("utf-8")), [_parsed(source_text)],
        MatchConfidence.STRICT, reconstruct=True,
    )


def _bitrate_pair() -> tuple:
    """base and one source text holding the same track, diverging on ALBUM
    and BITRATE - the smallest input reaching a source pick over a track base
    owns. ALBUM is the divergence the conflict is raised for and BITRATE is
    the measured name that rides along in attrs (DL-325, DL-327)."""
    base_text = _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, "")
    source_text = _nml(
        _entry("A", "Song", "track.mp3", time="100.0").replace(*_diverged("128")), 1, ""
    )
    return base_text, source_text


def test_a_source_pick_leaves_the_collection_at_bases_own_entry_count() -> None:
    """base keeps its own ENTRY for a track it already owns, so a source pick
    adds nothing to the COLLECTION and its ENTRIES attribute still counts
    base's entries (DL-004, DL-116).

    Observed with the base branch's entry_patches.append(...) replaced by
    `new_entries.append(picked)`, transplanting the named record's ENTRY
    beside base's instead of patching base's: AssertionError
    `assert 2 == 1`, the output COLLECTION holding two ENTRY elements where
    base held one.
    """
    base_text, source_text = _bitrate_pair()
    result = _resolved(base_text, source_text, 1)
    assert result.output is not None
    assert _entry_count(result.output) == _entry_count(base_text)
    assert _entries_attr(result.output) == str(_entry_count(base_text))


def test_a_source_pick_leaves_one_entry_for_the_conflicting_location() -> None:
    """The primary key is derived from the location, so the merged collection
    holds at most one entry per LOCATION; that one entry reads the source's
    BITRATE and base's own value is nowhere in the output (DL-004, DL-116).

    Observed with the base branch's entry_patches.append(...) replaced by
    `new_entries.append(picked)`, transplanting the named record's ENTRY
    beside base's instead of patching base's: AssertionError
    `assert 2 == 1`, _files reading ['track.mp3', 'track.mp3'] - two entries
    sharing one LOCATION.
    """
    base_text, source_text = _bitrate_pair()
    result = _resolved(base_text, source_text, 1)
    assert result.output is not None
    assert _files(result.output).count("track.mp3") == 1
    assert 'BITRATE="128"' in result.output
    assert 'BITRATE="320"' not in result.output


def test_a_non_divergent_tracked_attribute_keeps_bases_value() -> None:
    """A source pick patches the group's divergent attributes and no others,
    so a tracked attribute the group agrees on stays base's own bytes
    (DL-118).

    Observed with the patched values extended to `{**values, "artist": ""}`,
    reaching an attribute every member of the group agrees on: AssertionError
    on `assert 'ARTIST="A"' in result.output`, base's own ARTIST value absent
    from the output.
    """
    base_text, source_text = _bitrate_pair()
    result = _resolved(base_text, source_text, 1)
    assert result.output is not None
    assert 'ARTIST="A"' in result.output
    assert 'FILESIZE="16"' in result.output


def test_a_divergent_attribute_whose_carrier_base_lacks_is_written_in_child_order() -> None:
    """collection_records reads an absent ALBUM as the empty string, so an
    album base lacks and the source carries is divergent and was on the row
    the operator settled; it is written into base's entry at the position the
    fixed child order gives it rather than appended (DL-119, DL-127).

    Observed with the values comprehension filtered to `if
    getattr(winner, attr)`, honouring only the attributes base already
    carries a value for:
    AssertionError `assert ['LOCATION', 'INFO'] == ['LOCATION', 'ALBUM',
    'INFO']`, the patched entry carrying no ALBUM child at all.
    """
    base_text = _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, "")
    source_text = _nml(_album_entry("A", "Song", "track.mp3", "Disc", time="100.0"), 1, "")
    result = _resolved(base_text, source_text, 1)
    assert result.output is not None
    assert _entry_count(result.output) == 1
    assert _child_tags(result.output, "track.mp3") == ["LOCATION", "ALBUM", "INFO"]
    assert 'ALBUM TITLE="Disc"' in result.output


def test_a_source_pick_of_an_empty_value_keeps_the_carrier_and_its_siblings() -> None:
    """An empty winning value is written as an empty attribute rather than by
    removing the carrier, so base's INFO stays with the attributes the pick
    says nothing about intact (DL-119).

    Observed with the values comprehension filtered to `if
    getattr(named_record, attr)`, skipping an empty winning value:
    AssertionError on `assert 'BITRATE=""' in result.output`, base's own
    BITRATE="320" left standing.
    """
    base_text = _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, "")
    source_text = _nml(
        _entry("A", "Song", "track.mp3", time="100.0")
        .replace('BITRATE="320"', 'BITRATE=""')
        .replace(*_DIVERGED_ARTIST),
        1, "",
    )
    result = _resolved(base_text, source_text, 1)
    assert result.output is not None
    assert _child_tags(result.output, "track.mp3") == ["LOCATION", "INFO"]
    assert 'BITRATE=""' in result.output
    assert 'ARTIST="A2"' in result.output
    assert 'PLAYTIME_FLOAT="100.0"' in result.output
    assert 'FILESIZE="16"' in result.output


def test_a_crlf_base_file_keeps_its_line_endings_through_a_patch() -> None:
    """Every line terminator in an output is a byte copied from an input, so a
    CRLF base yields an output holding base's own CRLF count and no bare LF; an
    inserted child copies the byte run that indents its following sibling
    rather than composing whitespace, so it carries that run's CRLF and adds
    exactly the one line that copied run is (DL-128).

    Observed with the patch call reading
    `patch_entry_attributes(span.text(base_source).replace("\r\n", "\n"),
    values)`, composing the patched span's terminators instead of copying
    them: AssertionError `assert 17 == 22`, the output holding 17 CRLF where
    base held 22.
    """
    base_text = _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, "").replace("><", ">\n<")
    base_text = base_text.replace("\r\n", "\n").replace("\n", "\r\n")

    substituted = _resolved(
        base_text,
        _nml(
            _entry("A", "Song", "track.mp3", time="100.0")
            .replace('BITRATE="320"', 'BITRATE="128"')
            .replace(*_DIVERGED_ARTIST),
            1, "",
        ),
        1,
    )
    assert substituted.output is not None
    assert 'BITRATE="128"' in substituted.output
    assert 'ARTIST="A2"' in substituted.output
    assert substituted.output.count("\r\n") == base_text.count("\r\n")
    assert substituted.output.count("\n") - substituted.output.count("\r\n") == 0

    inserted = _resolved(
        base_text, _nml(_album_entry("A", "Song", "track.mp3", "Disc", time="100.0"), 1, ""), 1
    )
    assert inserted.output is not None
    assert 'ALBUM TITLE="Disc"' in inserted.output
    assert inserted.output.count("\n") - inserted.output.count("\r\n") == 0
    assert inserted.output.count("\r\n") == base_text.count("\r\n") + 1


def test_collection_entries_added_after_a_source_pick_matches_a_base_pick() -> None:
    """collection_entries_added counts entries actually added to the
    COLLECTION, and a source pick on a group base already owns adds none, so
    it reads what a base pick over the same inputs leaves (DL-124).

    Observed with the base branch's entry_patches.append(...) replaced by
    `new_entries.append(picked)`, transplanting the named record's ENTRY
    beside base's instead of patching base's: AssertionError
    `assert 1 == 0`, collection_entries_added reading 1 after the source pick
    where the base pick over the same inputs left 0.
    """
    base_text, source_text = _bitrate_pair()
    picked_source = _resolved(base_text, source_text, 1)
    picked_base = _resolved(base_text, source_text, 0)
    assert picked_source.stats["collection_entries_added"] == picked_base.stats["collection_entries_added"]
    assert picked_source.stats["collection_entries_added"] == 0


def test_a_base_less_group_still_transplants_under_keep_first_and_keep_last() -> None:
    """Where no base record occupies the collection slot the picker still
    answers which non-base copy survives and its ENTRY is transplanted
    verbatim, which is the branch base_member is None alone selects (DL-117).

    Observed with the transplant branch read as `if base_member is None and
    picked is not None:`, so a base-less group no resolution names fell to
    the else branch: TypeError: cannot unpack non-iterable NoneType object,
    raised where that branch unpacks base_member.
    """
    base_text = _nml(_entry("Z", "Base", "base.mp3"), 1, "")
    first = _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, "")
    second = _nml(
        _entry("A", "Song", "track.mp3", time="100.0").replace(*_diverged("128")), 1, ""
    )
    for policy, bitrate in (("keep-first", "320"), ("keep-last", "128")):
        result = assemble_output(
            base_text, parse_xml_bytes(base_text.encode("utf-8")),
            [_parsed(first), _parsed(second)], MatchConfidence.STRICT, policy,
        )
        assert result.output is not None, policy
        assert _entry_count(result.output) == 2, policy
        assert _files(result.output).count("track.mp3") == 1, policy
        assert 'BITRATE="%s"' % bitrate in _collection_of(result.output), policy
        assert result.stats["collection_entries_added"] == 1, policy


def test_a_source_pick_with_reconstruct_unset_patches_bases_entry() -> None:
    """The replacement pass is entered on the entry patches alone, so it is
    reached by a run that asks for no playlist reconstruction (DL-121).

    Observed with the apply and its re-parse indented back inside the `if
    reconstruct:` block: AssertionError on `assert 'BITRATE="128"' in
    result.output`, the run leaving base's entry unpatched.
    """
    base_text, source_text = _bitrate_pair()
    result = _resolved(base_text, source_text, 1, reconstruct=False)
    assert result.output is not None
    assert _entry_count(result.output) == 1
    assert 'BITRATE="128"' in result.output
    assert 'BITRATE="320"' not in result.output


def test_a_source_pick_and_a_reconstruction_share_one_replacement_pass() -> None:
    """Entry patches and rebuilt playlists are applied to base_source in one
    forward pass whose cursor reads the original text every offset was
    measured on, so both land and base's PLAYLIST keeps its own node and
    position (DL-121).

    Observed with _apply_replacements' `cursor = end_at` changed to
    `cursor = start_at + len(fragment)`, so the cursor advanced by the
    fragment's length in the rewritten text rather than to the replaced
    span's end in the original: lxml.etree.XMLSyntaxError: Opening and
    ending tag mismatch: COLLECTION line 2 and ENTRY, line 2, column 471,
    raised re-parsing base_source.
    """
    track_key = "C:" + "/:Music/:" + "track.mp3"
    two_key = "C:" + "/:Music/:" + "two.mp3"
    two = _entry("B", "Two", "two.mp3")
    base_text = _nml(
        _entry("A", "Song", "track.mp3", time="100.0") + two, 2,
        _playlist("MySet", [track_key], "uuid-base"),
    )
    # The source carries an ALBUM base's entry lacks, so the entry patch is
    # longer than the span it replaces, so the later playlist offset lands
    # correctly only under an apply that measures against the original text
    # rather than against the text the earlier fragment has already grown.
    source_text = _nml(
        _album_entry("A", "Song", "track.mp3", "Disc", time="100.0", bitrate="128") + two, 2,
        _playlist("MySet", [two_key, track_key], "uuid-prev"),
    )
    result = _resolved(base_text, source_text, 1, reconstruct=True)
    assert result.output is not None
    assert _entry_count(result.output) == 2
    assert 'BITRATE="128"' in result.output
    assert _child_tags(result.output, "track.mp3") == ["LOCATION", "ALBUM", "INFO"]
    assert _names(result.output) == ["MySet"]
    assert _pkeys(result.output) == [track_key, two_key]
    # Base's own NODE, its UUID and its position among the root SUBNODES are
    # base's own bytes: only the PLAYLIST element inside it is rebuilt.
    assert (
        result.output[result.output.index("</COLLECTION>"): result.output.index("<PLAYLIST ")]
        == base_text[base_text.index("</COLLECTION>"): base_text.index("<PLAYLIST ")]
    )
    assert "uuid-prev" not in result.output


def test_an_overlapping_replacement_span_is_refused_rather_than_written() -> None:
    """The forward apply enforces the disjointness the COLLECTION and
    PLAYLISTS spans have rather than assuming it: a span starting before its
    predecessor's end raises naming both offsets, where a silent pass would
    drop the bytes the two spans straddle (DL-121).

    Observed with the `if start_at < cursor: raise ValueError(...)` check
    deleted from _apply_replacements: `Failed: DID NOT RAISE <class
    'ValueError'>`, the call returning 'AA<first><second>E' - the 'CD' the
    two spans straddle dropped and no error raised.
    """
    with pytest.raises(ValueError) as excinfo:
        _apply_replacements("AABBCCDE", [(2, 6, "<first>"), (4, 7, "<second>")])
    assert "offset 4" in str(excinfo.value)
    assert "offset 6" in str(excinfo.value)


def test_a_duplicate_playlist_name_abort_discards_the_source_picks_patch() -> None:
    """The reconstruction block's aborts return above the apply, so a refused
    run discards its entry patches with everything else and no rewritten
    base_source reaches an output (DL-121).

    Observed with the duplicate_playlist_name abort's return replaced by
    `duplicate_names = list(duplicate_names)`, letting the run continue past
    it: AssertionError `assert '<?xml version="1.0" ... </NML>' is None` -
    the refused run returned an output carrying the patch, with errors empty
    and its playlist_name row recorded as ambiguous.
    """
    track_key = "C:" + "/:Music/:" + "track.mp3"
    entries = _entry("A", "Song", "track.mp3", time="100.0")
    base_text = _nml(
        entries, 1, _playlist("MySet", [], "uuid-base") + _playlist("MySet", [track_key], "uuid-base2")
    )
    source_text = _nml(
        entries.replace(*_diverged("128")), 1, _playlist("MySet", [track_key], "uuid-prev")
    )
    result = _resolved(base_text, source_text, 1, reconstruct=True)
    assert result.output is None
    assert result.errors == ["ambiguous_playlist_name playlist=MySet"]


def test_a_source_pick_on_two_base_records_patches_the_first_only() -> None:
    """A group with several base records has no single right redirect target,
    so the pick patches base_members[0]'s entry alone and the group's non-base
    key stays ambiguous. The reconstruction places that entry on the record
    the merge redirects the key to - base_members[0] - and counts it, rather
    than dropping the entry or refusing the run (DL-094, DL-122, DL-230).

    Observed with the append written as a loop over every base member,
    `for _base_idx, base_rec in base_members:`: AssertionError `assert 2 ==
    1` on the collection's count of BITRATE="128", both base entries carrying
    the source's value.
    """
    a1 = _entry("A", "Song", "a1.mp3", time="100.0")
    a2 = _entry("A", "Song", "a2.mp3", time="100.0")
    a3 = _entry("A", "Song", "a3.mp3", time="100.0").replace(*_diverged("128"))
    other = _entry("B", "Other", "other.mp3")
    # The incoming playlist holds a track base's does not, so its redirected
    # key sequence differs from base's and the run reaches the rebuild rather
    # than skipping the name as one that already matches.
    base_text = _nml(a1 + a2 + other, 3, _playlist("MySet", ["C:" + "/:Music/:" + "a1.mp3"], "uuid-base"))
    source_text = _nml(
        a3 + other, 2,
        _playlist("MySet", ["C:" + "/:Music/:" + "other.mp3", "C:" + "/:Music/:" + "a3.mp3"], "uuid-prev"),
    )

    merged = _resolved(base_text, source_text, 1)
    assert merged.output is not None
    assert _entry_count(merged.output) == 3
    assert _collection_of(merged.output).count('BITRATE="128"') == 1
    first, second, _other = re.findall(r"<ENTRY .*?</ENTRY>", _collection_of(merged.output), re.DOTALL)
    assert 'FILE="a1.mp3"' in first and 'BITRATE="128"' in first
    assert 'FILE="a2.mp3"' in second and 'BITRATE="320"' in second

    rebuilt = _resolved(base_text, source_text, 1, reconstruct=True)
    assert rebuilt.output is not None
    assert rebuilt.errors == []
    # a3's key redirects to a1, which base's own playlist already holds, so
    # the rebuilt list is base's entry then the one it lacked - and the run
    # reports the one entry that landed on a track base holds twice.
    assert _pkeys(rebuilt.output) == [
        "C:" + "/:Music/:" + "a1.mp3",
        "C:" + "/:Music/:" + "other.mp3",
    ]
    assert rebuilt.stats["entries_on_duplicated_tracks"] == 1
    assert rebuilt.stats["playlists_on_duplicated_tracks"] == {"MySet": 1}
    assert rebuilt.stats["playlists_reconstructed"] == 1


def test_the_base_input_file_is_byte_identical_across_a_patching_run(tmp_path: Path) -> None:
    """What a source pick rewrites is the output's copy of base's entry; the
    base input file on disk is never written (DL-123).

    Observed with the patched values replaced by `{}`: AssertionError: the
    run patched nothing - the output equalled the base file's own text, while
    the file on disk stayed byte-identical either way.
    """
    base_path = tmp_path / "base.nml"
    base_path.write_text(
        _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, ""), encoding="utf-8", newline=""
    )
    before = base_path.read_bytes()
    _base, source_text = _bitrate_pair()
    result = _resolved(before.decode("utf-8"), source_text, 1)
    assert result.output is not None
    assert result.output != before.decode("utf-8"), "the run patched nothing"
    assert base_path.read_bytes() == before, "base input was modified"


def test_a_source_pick_leaves_one_collection_entry_for_the_shared_location() -> None:
    """A source pick over a track base already owns settles the group inside
    base's own ENTRY, so the merged COLLECTION holds one entry for that
    LOCATION and the run introduces no second entry for it (DL-004).

    Observed with the base-holding pick branch's entry_patches.append(...)
    replaced by `new_entries.append((picked[0], named_record))`,
    transplanting the named record's ENTRY beside base's own:
    AssertionError on `assert result.output is not None`, the result
    reading errors=['entry_location_collision key=C:/:Music/:track.mp3']
    and output=None.
    """
    base_text, base_root, contributions = _diverging_pair()
    row = _reported(base_text, base_root, contributions)
    result = assemble_output(
        base_text, base_root, contributions, MatchConfidence.STRICT,
        resolutions={row.identity_key: _pair_naming(row, 1)},
    )
    assert result.output is not None
    assert result.errors == []
    assert _entry_count(result.output) == 1
    assert _files(result.output) == ["track.mp3"]


def test_a_source_pick_reparses_to_bases_own_collection_entry_count() -> None:
    """The replacement pass rewrites attribute values inside a base entry's
    own span, so the COLLECTION re-parsed from the rewritten base_source
    holds the two entries base held and the other track survives the patch
    (DL-121).

    Observed with the entry patch's replacement end offset `span.end`
    replaced by `base_source.index("</ENTRY>", span.end) + len("</ENTRY>")`,
    widening the span past the patched entry's boundary over the following
    one: AssertionError on `assert result.output is not None`, the result
    reading errors=['collection_entry_count base=2 assembled=1'] and
    output=None.
    """
    base_text = _nml(
        _entry("A", "Song", "track.mp3", time="100.0") + _entry("B", "Other", "other.mp3"), 2, ""
    )
    _base, source_text = _bitrate_pair()
    result = _resolved(base_text, source_text, 1)
    assert result.output is not None
    assert result.errors == []
    assert _entry_count(result.output) == 2
    assert _files(result.output) == ["track.mp3", "other.mp3"]


def test_every_emitted_playlist_key_names_an_emitted_collection_entry() -> None:
    """Every PRIMARYKEY in the assembled text names an entry the assembled
    COLLECTION holds, read off the text the run returns rather than off the
    inputs and the redirect mapping the pass above reads.

    That pass answers the same question from what the keys ought to be, so
    it cannot see a fragment emitted carrying something else; this one reads
    the artefact. Observed with `output = builder.build()` replaced by
    `builder.build().replace('KEY="C:/:Music/:two.mp3"',
    'KEY="C:/:Music/:ghost.mp3"')`, corrupting only the emitted text and
    leaving old_to_new_key untouched so the input-side pass still computed a
    clean expectation: the run returned
    errors=['emitted_key_unresolved key=C:/:Music/:ghost.mp3'] with
    output=None, where without the audit it returned that output.
    """
    track_key = "C:" + "/:Music/:" + "track.mp3"
    base_text = _nml(
        _entry("A", "Song", "track.mp3", time="100.0"), 1,
        _playlist("MySet", [track_key], "uuid-base"),
    )
    source_text = _nml(
        _entry("A", "Song", "track.mp3", time="100.0").replace(*_diverged("128")),
        1,
        _playlist("MySet", [track_key], "uuid-prev"),
    )
    result = _resolved(base_text, source_text, 1, reconstruct=True)

    assert result.output is not None
    assert result.errors == []
    collection_text = result.output.split("</COLLECTION>")[0]
    entries = {
        f"{volume}{dir_value}{file_name}"
        for dir_value, file_name, volume in re.findall(
            r'<LOCATION\b[^>]*\bDIR="([^"]*)"[^>]*\bFILE="([^"]*)"[^>]*\bVOLUME="([^"]*)"',
            collection_text,
        )
    }
    emitted = set(re.findall(r'<PRIMARYKEY\b[^>]*\bKEY="([^"]*)"', result.output))
    assert emitted
    assert sorted(emitted - entries) == []


def test_a_reconstruction_run_counts_the_empty_playlists_it_filled_and_names_the_rest() -> None:
    """A run reports how many base playlists held nothing before it, how
    many of those it filled, and the names of the ones it could not, so a
    caller reporting the run reads it off the run rather than walking the
    base collection a second time.

    A rebuilt playlist and a refilled one are not the same set: a
    playlist already holding tracks is rebuilt where the source holds
    more of them, and it was never empty. The fixture holds one of each,
    so a count of rebuilds standing in for a count of refills is visible.

    Mutation: `stats["refilled_playlists"] = len(empty_names &
    set(reconstructed))` was changed to `= len(reconstructed)`.
    Observed:
        E       assert 2 == 1
        E        +  where 2 = {'collection_entries_added': 0, 'collection_entries_total': 2, 'conflicts_reported': 0, 'empty_playlists': 2, ...}['refilled_playlists']
    """
    one_key = "C:" + "/:Music/:" + "one.mp3"
    two_key = "C:" + "/:Music/:" + "two.mp3"
    entries = _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3")
    base_text = _nml(
        entries, 2,
        _playlist("Lost", [], "uuid-lost")
        + _playlist("Never held", [], "uuid-never")
        + _playlist("Partial", [one_key], "uuid-partial"),
    )
    source_text = _nml(
        entries, 2,
        _playlist("Lost", [one_key, two_key], "uuid-src")
        + _playlist("Partial", [one_key, two_key], "uuid-src-two"),
    )
    result = _assembled(base_text, source_text)
    assert result.output is not None
    assert result.stats["empty_playlists"] == 2
    assert result.stats["refilled_playlists"] == 1
    assert result.stats["unfilled_playlists"] == ["Never held"]
    # Both were rebuilt; only the one that held nothing was refilled.
    assert sorted(result.stats["reconstructed_playlists"]) == ["Lost", "Partial"]


def test_the_reported_entry_total_is_the_count_the_output_declares() -> None:
    """The COLLECTION ENTRIES the output carries and the total the stats
    report are one number read once, so a caller printing the size of the
    collection about to be written prints what that file says.

    Mutation: `stats["collection_entries_total"] = collection_total` was
    changed to `= collection_total + 1`. Observed:
        E       assert 3 == 2
        E        +  where 3 = {'collection_entries_added': 0, 'collection_entries_total': 3, 'conflicts_reported': 0, 'empty_playlists': 0, ...}['collection_entries_total']
    """
    entries = _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3")
    base_text = _nml(entries, 2, _playlist("Intact", [], "uuid-intact"))
    result = _assembled(base_text, base_text)
    assert result.output is not None
    declared = int(re.search(r'<COLLECTION ENTRIES="(\d+)"', result.output).group(1))
    assert result.stats["collection_entries_total"] == declared


def _folder(name: str, inner: str) -> str:
    """A FOLDER node holding the playlists in `inner`, which is where a
    collection puts a playlist whose name another folder also uses."""
    return (
        f'<NODE TYPE="FOLDER" NAME="{name}">'
        f'<SUBNODES COUNT="{inner.count(chr(60) + "NODE")}">{inner}</SUBNODES>'
        "</NODE>"
    )


def test_one_name_in_two_folders_is_two_playlists() -> None:
    """A playlist is identified by the folder path it sits at, which is
    what Traktor's own SORTING_INFO PATH names it by, not by its bare
    NAME. A real collection reuses a name freely across folders - one
    measured collection holds 1187 playlists under 768 names - so keying
    by name calls those ambiguous and refuses to rebuild anything
    (DL-228).

    Both empty playlists here are named `Jan`, in folders `2020` and
    `2024`, and each has a counterpart of its own in the source holding
    different tracks. Each is rebuilt from its own counterpart.

    Mutation: `base_by_path` was built from `node.attrib["NAME"]` in
    place of the path, and `incoming_by_path` with it. Observed:
        E       AssertionError: assert ['ambiguous_p...playlist=Jan'] == []
        E
        E         Left contains one more item: 'ambiguous_playlist_name playlist=Jan'
        E         Use -v to get more diff
    """
    one_key = "C:" + "/:Music/:" + "one.mp3"
    two_key = "C:" + "/:Music/:" + "two.mp3"
    entries = _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3")
    base_text = _nml(
        entries, 2,
        _folder("2020", _playlist("Jan", [], "uuid-2020"))
        + _folder("2024", _playlist("Jan", [], "uuid-2024")),
    )
    source_text = _nml(
        entries, 2,
        _folder("2020", _playlist("Jan", [one_key], "uuid-src-2020"))
        + _folder("2024", _playlist("Jan", [two_key], "uuid-src-2024")),
    )
    result = _assembled(base_text, source_text)
    assert result.errors == []
    assert result.output is not None
    # Keyed by path, so the two are told apart in the report as well.
    assert result.stats["reconstructed_playlists"] == {
        "2020\\Jan": 1,
        "2024\\Jan": 1,
    }
    assert result.stats["empty_playlists"] == 2
    assert result.stats["refilled_playlists"] == 2
    # Each took its own counterpart's track rather than the union of both.
    first = result.output.index("uuid-2020")
    second = result.output.index("uuid-2024")
    assert result.output.count(one_key, first, second) == 1
    assert result.output.count(two_key, first, second) == 0


def test_one_path_held_twice_is_still_refused() -> None:
    """Two playlists at the same path have no single playlist to rebuild
    or to rebuild from, so the run refuses rather than picking one by
    document order (DL-098). This is the collision the name check was
    reaching for; it is rare where a name collision is not.

    Mutation: the `duplicate_paths` abort was deleted from splice.py.
    Observed:
        E       AssertionError: assert [] == ['ambiguous_p...st=2020\\\\Jan']
        E
        E         Right contains one more item: 'ambiguous_playlist_name playlist=2020\\\\Jan'
        E         Use -v to get more diff
    """
    one_key = "C:" + "/:Music/:" + "one.mp3"
    entries = _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3")
    base_text = _nml(
        entries, 2,
        _folder(
            "2020",
            _playlist("Jan", [], "uuid-a") + _playlist("Jan", [], "uuid-b"),
        ),
    )
    source_text = _nml(
        entries, 2, _folder("2020", _playlist("Jan", [one_key], "uuid-src")),
    )
    result = _assembled(base_text, source_text)
    assert result.errors == ["ambiguous_playlist_name playlist=2020\\Jan"]
    assert result.output is None


def test_a_playlist_that_moved_folders_pairs_on_its_name() -> None:
    """A playlist with no counterpart at its own path is still the same
    playlist if it moved folders between the two collections, so it pairs
    on its name where that name names exactly one playlist on each side.
    Where it does not, nothing says which of them it is and it is left
    alone rather than rebuilt from a guess (DL-228).

    Mutation: the by-name fallback was removed from the loop, leaving
    `continue` where a path has no counterpart. Observed:
        E       AssertionError: assert {} == {'2024\\\\Jan': 1}
        E
        E         Right contains 1 more item:
        E         {'2024\\\\Jan': 1}
        E         Use -v to get more diff
    """
    one_key = "C:" + "/:Music/:" + "one.mp3"
    entries = _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3")
    base_text = _nml(
        entries, 2, _folder("2024", _playlist("Jan", [], "uuid-base")),
    )
    source_text = _nml(
        entries, 2, _folder("archive", _playlist("Jan", [one_key], "uuid-src")),
    )
    result = _assembled(base_text, source_text)
    assert result.errors == []
    assert result.stats["reconstructed_playlists"] == {"2024\\Jan": 1}

    # Two playlists share the name, so the move cannot be followed: which
    # of them the source's copy belongs to is not said by anything.
    ambiguous_base = _nml(
        entries, 2,
        _folder("2024", _playlist("Jan", [], "uuid-a"))
        + _folder("2020", _playlist("Jan", [], "uuid-b")),
    )
    unfollowable = _assembled(ambiguous_base, source_text)
    assert unfollowable.errors == []
    assert unfollowable.stats["reconstructed_playlists"] == {}


def test_a_name_holding_a_tab_is_not_read_as_two_different_keys() -> None:
    """The emitted-key self-check compares values, not their escaping.

    A LOCATION carried through verbatim keeps the escaping its own file
    used, while a PRIMARYKEY inside a re-serialised playlist carries the
    escaping the serialiser chose. A collection measured for this holds a
    file name with a tab in it, written `&#x9;` on both sides of its own
    file; the rebuilt playlist writes the same tab `&#09;`. The same
    value, spelled two ways, read as a key naming no entry - and the run
    refuses over a name the output spells correctly either way (DL-231).

    Mutation: the two html.unescape calls were removed from the check.
    Observed:
        E       AssertionError: assert ['emitted_key...mp;&#9;b.mp3'] == []
        E
        E         Left contains one more item: 'emitted_key_unresolved key=C:/:Music/:a&amp;&#9;b.mp3'
        E         Use -v to get more diff
    """
    awkward = "a&amp;&#x9;b.mp3"
    key = "C:" + "/:Music/:" + awkward
    other_key = "C:" + "/:Music/:" + "other.mp3"
    entries = _entry("A", "One", awkward) + _entry("B", "Other", "other.mp3")
    base_text = _nml(entries, 2, _playlist("MySet", [key], "uuid-base"))
    source_text = _nml(entries, 2, _playlist("MySet", [key, other_key], "uuid-src"))
    result = _assembled(base_text, source_text)
    assert result.errors == []
    assert result.output is not None
    # The rebuilt playlist holds both, the awkward name among them.
    assert result.stats["reconstructed_playlists"] == {"MySet": 2}


def test_an_entry_on_a_track_the_base_holds_twice_is_placed_and_counted() -> None:
    """A playlist entry whose identity group holds more than one base
    record is placed on the record the merge redirects that key to, and
    the run reports how many landed that way and in which playlists.
    Refusing the run instead answers nothing an operator can act on: the
    duplicates are in their collection and no control here removes them
    (DL-094, DL-122, DL-230).

    Mutation: `placed = sum(1 for key in merged if key in
    redirected_here)` was changed to `placed = 0`. Observed:
        E       assert 0 == 1
    """
    a1 = _entry("A", "Song", "a1.mp3", time="100.0")
    a2 = _entry("A", "Song", "a2.mp3", time="100.0")
    other = _entry("B", "Other", "other.mp3")
    a1_key = "C:" + "/:Music/:" + "a1.mp3"
    a2_key = "C:" + "/:Music/:" + "a2.mp3"
    other_key = "C:" + "/:Music/:" + "other.mp3"
    # Base holds the same track twice, so the source's entry for it has
    # two candidate redirect targets.
    base_text = _nml(a1 + a2 + other, 3, _playlist("MySet", [], "uuid-base"))
    source_text = _nml(
        a1 + other, 2, _playlist("MySet", [a1_key, other_key], "uuid-src"),
    )
    result = _assembled(base_text, source_text)
    assert result.errors == []
    assert result.output is not None
    assert result.stats["entries_on_duplicated_tracks"] == 1
    assert result.stats["playlists_on_duplicated_tracks"] == {"MySet": 1}
    # The playlist was rebuilt rather than skipped, and the entry landed
    # on the first of the two records base holds for that track.
    assert result.stats["reconstructed_playlists"] == {"MySet": 2}
    assert _pkeys(result.output) == [a1_key, other_key]
    assert a2_key not in _pkeys(result.output)


def test_a_base_playlist_keeps_its_resolvable_entries_when_one_names_nothing(tmp_path: Path) -> None:
    """A base playlist the run does not rebuild, carrying one entry for a
    track no collection in the run holds: the run writes, that playlist
    keeps its other two entries, and the dangling one is gone.

    Mutation: in splice.assemble_output, the drop pass's guard
    `if playlist_elem is None or id(playlist_elem) in rebuilt_playlists:`
    replaced by `if True:`, so no base playlist is patched. Observed:
    `AssertionError: assert 2 == 0` on exit_code, with stderr
    `unresolved_reference playlist=Keep key=C:/:Music/:ghost.mp3` and
    `splice_aborted=true` - the whole run refused over the one entry.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("Keep", [_key("one"), _key("ghost"), _key("two")], "uuid-base"),
        _playlist("Elsewhere", [_key("three")], "uuid-prev"),
    )
    assert result.exit_code == 0
    assert _pkeys(text) == [_key("one"), _key("two"), _key("three")]
    assert 'ENTRIES="2" TYPE="LIST" UUID="uuid-base"' in text


def test_a_rebuilt_playlists_union_drops_the_member_that_names_nothing(tmp_path: Path) -> None:
    """The reconstruction pre-pass builds a playlist from the union of
    base's and the older collection's entries. A union member naming a
    track no collection holds is dropped from the rebuild, and the
    playlist is written with what survives.

    Mutation: in splice.assemble_output, the pre-pass line
    `unresolvable = [key for key in merged if key not in valid_keys]`
    replaced by `unresolvable = []`. Observed: `assert 2 == 0` on
    exit_code, with stderr `unresolved_reference playlist=MySet
    key=C:/:Music/:ghost.mp3` and `splice_aborted=true`.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("MySet", [], "uuid-base"),
        _playlist("MySet", [_key("one"), _key("ghost"), _key("two")], "uuid-prev"),
    )
    assert result.exit_code == 0
    assert _names(text) == ["MySet"]
    assert _pkeys(text) == [_key("one"), _key("two")]


def test_an_imported_playlist_drops_the_entry_that_names_nothing(tmp_path: Path) -> None:
    """A playlist that exists only in the older collection is imported
    whole. One of its entries naming a track no collection holds is
    dropped from the imported fragment, and its ENTRIES count is restated
    from what survives.

    Mutation: in splice.assemble_output, the import_playlists call's
    `valid_keys` argument replaced by `None`, so the import pass judges
    nothing. Observed: `AssertionError: assert 2 == 0` on exit_code, with
    stderr `unresolved_reference playlist=Imported
    key=C:/:Music/:ghost.mp3` and `splice_aborted=true`.
    """
    result, text = _reconstruct(
        tmp_path,
        _playlist("BaseOnly", [_key("one")], "uuid-base"),
        _playlist("Imported", [_key("two"), _key("ghost"), _key("three")], "uuid-prev"),
    )
    assert result.exit_code == 0
    assert _names(text) == ["BaseOnly", "Imported"]
    assert _pkeys(text) == [_key("one"), _key("two"), _key("three")]
    assert 'ENTRIES="2"' in text.split('NAME="Imported"')[1]


def test_the_dropped_entries_are_counted_apart_from_the_tracks_they_name(tmp_path: Path) -> None:
    """One missing track sitting in two playlists is two dropped entries
    and one dropped track, and each playlist that lost one is named with
    its own count.

    Mutation: in splice.assemble_output,
    `stats["tracks_dropped_unresolvable"] = len({key for _, key in
    dropped_refs})` replaced by `len(dropped_refs)`, so one missing track
    in two playlists reads as two tracks. Observed: `assert 2 == 1` on
    tracks_dropped_unresolvable.
    """
    base_text = _nml(
        _E3,
        3,
        _playlist("First", [_key("one"), _key("ghost")], "uuid-a")
        + _playlist("Second", [_key("ghost"), _key("two")], "uuid-b"),
    )
    base_root = parse_xml_bytes(base_text.encode("utf-8"))
    result = assemble_output(
        base_text, base_root, [], MatchConfidence.STRICT, "keep-first", True
    )
    assert result.errors == []
    assert result.output is not None
    assert result.stats["entries_dropped_unresolvable"] == 2
    assert result.stats["tracks_dropped_unresolvable"] == 1
    assert result.stats["playlists_with_dropped_entries"] == {"First": 1, "Second": 1}


def test_a_dropped_entry_reports_every_key_that_left_with_it(tmp_path: Path) -> None:
    """An ENTRY is removed whole, so a second PRIMARYKEY on that same
    entry leaves with it even where the collection does hold that track.
    The run says so rather than losing it silently: the unresolvable key
    is what the entry was dropped for, and the resolvable one is reported
    apart from it (DL-232, DL-237).

    A Traktor playlist entry names one track, so entries_carried_away is
    empty in an ordinary run - which is what makes a filled one worth
    reading.

    Mutation: in playlists.drop_unresolvable_entries, the line
    `result.carried_away.extend(key for key in keys if key in valid_keys)`
    deleted. Observed:
        E       AssertionError: a resolvable key left the playlist unreported
        E       assert [] == ['C:/:Music/:one.mp3']
        E         Right contains one more item: 'C:/:Music/:one.mp3'
    """
    from traktor_nml.playlists import drop_unresolvable_entries
    from traktor_nml.xmlio import parse_xml_bytes

    playlist = parse_xml_bytes(
        (
            '<PLAYLIST ENTRIES="2" TYPE="LIST">'
            "<ENTRY>"
            f'<PRIMARYKEY TYPE="TRACK" KEY="{_key("one")}"></PRIMARYKEY>'
            f'<PRIMARYKEY TYPE="TRACK" KEY="{_key("ghost")}"></PRIMARYKEY>'
            "</ENTRY>"
            "<ENTRY>"
            f'<PRIMARYKEY TYPE="TRACK" KEY="{_key("two")}"></PRIMARYKEY>'
            "</ENTRY>"
            "</PLAYLIST>"
        ).encode("utf-8")
    )
    dropped = drop_unresolvable_entries(playlist, {_key("one"), _key("two")})

    assert dropped.entries == 1, "the entry count is entries, not keys"
    assert dropped.unresolvable == [_key("ghost")]
    assert dropped.carried_away == [_key("one")], (
        "a resolvable key left the playlist unreported"
    )
    # What the element now holds agrees with what was reported to have left.
    surviving = _pkeys(_ET_tostring(playlist))
    assert surviving == [_key("two")]
    assert playlist.attrib["ENTRIES"] == "1"


# ---------------------------------------------------------------- the tier
#
# What a divergence is put to the operator for, and what the run answers
# itself. Each guard below records the mutation applied to make it fail
# and the verbatim output observed under that mutation. This file is LF.
#
# One guard per behaviour on each side of the tier: a measured-only
# divergence settling, an editorial divergence standing as an unresolved
# conflict, and a mixed divergence doing exactly one of the two. Every
# guard asserting conflict behaviour builds its fixture from an editorial
# divergence, because an editorial divergence is what a conflict is
# raised for; a guard asserting that a measured value travels with the
# winning record reads the settled row, which is where a measured-only
# divergence is reported (DL-325, DL-327).
#
# Every winner assertion reads the (input index, primary key) pair rather
# than the key alone: both members of a settled group describe the one
# LOCATION and carry the identical primary key, so a guard reading the key
# alone is green whichever record won (DL-148, DL-189).

_TIER_KEY = "C:" + "/:Music/:Sets/:Deep/:" + "one.mp3"

# One record's tracked values, which a fixture below moves one name of at a
# time. The numbers are the user's own collection pair's shape: an 8 MB
# file, a 100-second track and a 320 kbps encode as Traktor records them.
_TIER_VALUES = {
    "artist": "A",
    "title": "One",
    "album": "Alb",
    "filesize": "8192",
    "playtime_float": "100.0",
    "bitrate": "320000",
}


def _tier_entry(values: dict) -> str:
    """One ENTRY carrying every tracked attribute as a caller-set value,
    three folders deep so the path_suffix_3 tier strict admits groups two of
    them whatever they disagree on - including a pair disagreeing on ARTIST
    and FILESIZE at once, which no other strict tier would group."""
    return _deep_entry(
        values["artist"],
        values["title"],
        values["album"],
        values["filesize"],
        values["playtime_float"],
        values["bitrate"],
    )


def _tier_copies(divergence: dict, count: int = 2, **constants) -> list:
    """count collection texts for the one LOCATION, the record in copy i
    carrying divergence[attr][i] for each name divergence holds and
    _TIER_VALUES[attr] for every other name.

    The divergence is stated as a mapping of attribute name to the values
    the copies hold for it, which is how the tier reads it, rather than by
    editing XML. constants override _TIER_VALUES for every copy alike, which
    is how a second track in one run is made a second identity group rather
    than a fourth member of the first: two records agreeing on artist, title,
    filesize and playtime share the artist_title_size_time key whatever their
    file names are."""
    texts = []
    for i in range(count):
        values = dict(_TIER_VALUES, **constants)
        for attr, side_values in divergence.items():
            values[attr] = side_values[i]
        texts.append(_nml(_tier_entry(values), 1, ""))
    return texts


def _tier_pair(divergence: dict) -> tuple:
    """base, base's parsed root and one contribution, the two describing the
    one LOCATION and differing exactly on the names divergence holds."""
    base_text, source_text = _tier_copies(divergence)
    return base_text, parse_xml_bytes(base_text.encode("utf-8")), [_parsed(source_text)]


def _tier_two_groups(editorial: dict, measured: dict) -> tuple:
    """base and one contribution holding two tracks: one group diverging on
    the editorial names given and one on the measured names given, so a run
    reports a conflict and a settled row at once.

    The second track is the same deep folder under another file name and
    another TITLE, so path_suffix_3 groups its two copies the way it groups
    the first's while no tier joins the two groups."""
    first_base, first_source = _tier_copies(editorial)
    second_base, second_source = (
        text.replace('FILE="one.mp3"', 'FILE="two.mp3"')
        for text in _tier_copies(measured, title="Two")
    )
    base_text = _nml(_entries_of(first_base) + _entries_of(second_base), 2, "")
    source_text = _nml(_entries_of(first_source) + _entries_of(second_source), 2, "")
    return base_text, parse_xml_bytes(base_text.encode("utf-8")), [_parsed(source_text)]


def _entries_of(nml_text: str) -> str:
    """The ENTRY elements a one-track collection text holds, so two of these
    texts compose one two-track collection without a second wrapper."""
    collection = _collection_of(nml_text)
    return collection[collection.index(">") + 1:]


def _tier_base_less(divergence: dict) -> tuple:
    """base holding an unrelated track and two sources holding the one deep
    LOCATION, differing on the names divergence holds.

    The group holds no base record, so the run-wide picker names the
    survivor. keep-last is passed by the guard that uses this, which makes
    the winner input 2 while the group's first member is input 1 - so a
    reading that took the first member rather than the winner cannot pass
    (DL-189)."""
    base_text = _nml(_entry("Z", "Other", "other.mp3", time="9.0"), 1, "")
    first, second = _tier_copies(divergence)
    return base_text, parse_xml_bytes(base_text.encode("utf-8")), [_parsed(first), _parsed(second)]


def test_a_measured_only_divergence_settles_and_reports_a_settled_row() -> None:
    """A base-and-source pair differing only in BITRATE assembles output
    with no conflict row, no unresolved abort, and one settled row naming
    the record the output keeps (DL-325, DL-328).

    Mutation: `settled_by_rule = bool(divergent_attrs) and not
    editorial_attrs` in _resolve_conflicts replaced by `settled_by_rule =
    False`, so the group took the conflict branch.
    Observed:
        AssertionError: assert [ConflictRow(...', '100.0')))] == []

          Left contains one more item: ConflictRow(identity_key='C:/:Music/:Sets/:Deep/:one.mp3', attrs='bitrate', resolution=None, member_keys=frozenset({'C...),))), agreed=(('artist', 'A'), ('title', 'One'), ('album', 'Alb'), ('filesize', '8192'), ('playtime_float', '100.0')))
          Use -v to get more diff
    """
    result = assemble_output(
        *_tier_pair({"bitrate": ("320000", "1411000")}), MatchConfidence.STRICT
    )
    assert result.conflict_rows == []
    assert result.errors == []
    assert result.output is not None
    (settled,) = result.settled_rows
    assert settled.identity_key == _TIER_KEY
    assert settled.attrs == ("bitrate",)
    assert settled.values_by_attr == (("bitrate", ("320000", "1411000")),)
    # The pair, not the key: both members describe the one LOCATION, so
    # the key equals identity_key and the input index is the half that
    # says which record won (DL-148).
    assert settled.winner == (0, _TIER_KEY)
    assert result.stats["groups_settled_by_rule"] == 1
    assert result.stats["conflicts_reported"] == 0


def test_an_editorial_divergence_is_still_put_to_the_operator() -> None:
    """A pair differing in ARTIST aborts an unresolved run exactly as it
    does today, and reports no settled row: the rule answered nothing for
    it.

    Mutation: the two halves of split_by_tier's result unpacked the other
    way round in _resolve_conflicts, so an ARTIST divergence read as a
    measured one and settled.
    Observed:
        assert '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD... TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS><SETS></SETS><INDEXING></INDEXING></NML>' is None
         +  where '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD... TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS><SETS></SETS><INDEXING></INDEXING></NML>' = SpliceResult(output='<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<NML VERSION="20"><HEAD PROGRAM="Traktor...t',), values_by_attr=(('artist', ('A', 'B')),), winner=(0, 'C:/:Music/:Sets/:Deep/:one.mp3'), outliers=())], errors=[]).output
    """
    result = assemble_output(*_tier_pair({"artist": ("A", "B")}), MatchConfidence.STRICT)
    assert result.output is None
    assert result.errors == ["unresolved_conflicts"]
    assert result.settled_rows == []
    (row,) = result.conflict_rows
    assert row.attrs == "artist"
    assert result.stats["groups_settled_by_rule"] == 0


def test_a_mixed_divergence_is_one_conflict_row_and_no_settled_row() -> None:
    """A group diverging on ARTIST and BITRATE reports one conflict row
    whose attrs reads artist, bitrate - every divergent name, so its CSV
    row and its resolve rail stand as they stand - and contributes no
    settled row, so its measured divergence is never reported twice
    (DL-329).

    Mutation: `if settled_by_rule:` in _resolve_conflicts relaxed to `if
    measured_attrs:`, so a group carrying any measured divergence reported a
    settled row.
    Observed:
        AssertionError: assert [SettledRow(i...890148831),))] == []

          Left contains one more item: SettledRow(identity_key='C:/:Music/:Sets/:Deep/:one.mp3', attrs=('bitrate',), values_by_attr=(('bitrate', ('320000', '.../:one.mp3'), outliers=(OutlierReading(attr='bitrate', low='320000', high='1411000', relative_gap=0.7732104890148831),))
          Use -v to get more diff
    """
    # keep-first so the run reaches the reporting branches rather than the
    # unresolved abort, which reports its row and moves on before the tier
    # divides anything.
    result = assemble_output(
        *_tier_pair({"artist": ("A", "B"), "bitrate": ("320000", "1411000")}),
        MatchConfidence.STRICT,
        "keep-first",
    )
    assert result.output is not None
    assert result.settled_rows == []
    (row,) = result.conflict_rows
    assert row.attrs == "artist,bitrate"
    assert row.resolution == "keep-first"
    assert result.stats["groups_settled_by_rule"] == 0
    assert result.stats["settled_groups_outlying"] == 0


def test_the_wide_filesize_pair_reads_as_an_outlier_and_the_drift_does_not() -> None:
    """17564 against 69203 is the .stem.m4a described twice and is worth
    reading; 8123 against 8124 is the 1 KB drift the pair is full of and
    is not (DL-330).

    Mutation: OUTLIER_BAND = 0.0 in metadata_tier.
    Observed:
        AssertionError: assert True is False
         +  where True = SettledRow(identity_key='C:/:Music/:Sets/:Deep/:one.mp3', attrs=('filesize',), values_by_attr=(('filesize', ('8123', '.../:one.mp3'), outliers=(OutlierReading(attr='filesize', low='8123', high='8124', relative_gap=0.00012309207287050715),)).is_outlier
    """
    wide = assemble_output(
        *_tier_pair({"filesize": ("17564", "69203")}), MatchConfidence.STRICT
    )
    drift = assemble_output(
        *_tier_pair({"filesize": ("8123", "8124")}), MatchConfidence.STRICT
    )
    assert wide.settled_rows[0].is_outlier is True
    assert drift.settled_rows[0].is_outlier is False
    assert wide.stats["settled_groups_outlying"] == 1
    assert drift.stats["settled_groups_outlying"] == 0
    (reading,) = wide.settled_rows[0].outliers
    assert (reading.attr, reading.low, reading.high) == ("filesize", "17564", "69203")


def test_a_settled_row_stands_on_a_run_that_aborts() -> None:
    """The rule answered those groups whatever the run's outcome, so a
    reader asking what was decided for the operator reads it off an
    aborted run too (DL-329).

    Mutation: settled_rows left off the early
    SpliceResult(output=None, ..., errors=["unresolved_conflicts"]) return.
    Observed:
        AssertionError: assert 0 == 1
         +  where 0 = len([])
         +    where [] = SpliceResult(output=None, stats={'inputs_merged': 1, 'identity_groups': 2, 'conflicts_reported': 1, 'groups_settled_by...ize', '8192'), ('playtime_float', '100.0'), ('bitrate', '320000')))], settled_rows=[], errors=['unresolved_conflicts']).settled_rows
    """
    result = assemble_output(
        *_tier_two_groups(
            editorial={"artist": ("A", "B")}, measured={"bitrate": ("320000", "1411000")}
        ),
        MatchConfidence.STRICT,
    )
    assert result.output is None
    assert result.errors == ["unresolved_conflicts"]
    assert len(result.conflict_rows) == 1
    assert len(result.settled_rows) == 1
    assert result.stats["groups_settled_by_rule"] == 1


def test_a_group_with_no_base_member_carries_the_winners_measured_values() -> None:
    """Where the group holds no base record the run-wide picker's winner is
    transplanted and its measured values travel with it, so the written file
    does not keep a number no record holds (DL-328).

    The pair is what the assertion reads: the two sources describe the one
    LOCATION and carry the one primary key, so a guard reading the key alone
    passes whichever of them was picked and this one would be green in the
    broken state (DL-148, DL-189).

    Mutation: _settled_row handed the group's first member in place
    of the winner (`*members[0]`).
    Observed:
        AssertionError: assert (1, 'C:/:Musi...eep/:one.mp3') == (2, 'C:/:Musi...eep/:one.mp3')

          At index 0 diff: 1 != 2
          Use -v to get more diff
    """
    result = assemble_output(
        *_tier_base_less({"filesize": ("17564", "69203")}),
        MatchConfidence.STRICT,
        "keep-last",
    )
    assert result.output is not None
    (settled,) = result.settled_rows
    assert settled.winner == (2, _TIER_KEY)
    # keep-last named input 2, and input 2's own FILESIZE is the one the
    # transplanted ENTRY span carries.
    assert 'FILESIZE="69203"' in _collection_of(result.output)
    assert 'FILESIZE="17564"' not in _collection_of(result.output)


def test_a_resolution_naming_a_settled_groups_record_is_inert() -> None:
    """A settled group is named by no resolution, so a mapping entry naming
    one of its records changes nothing: the group is settled by rule either
    way and no entry patch is collected for it (DL-105, DL-153, DL-328).

    Mutation: the resolutions lookup left reading `if divergent_attrs`
    in place of `if editorial_attrs`, so a pair naming a settled group's
    source record patched base's entry.
    Observed:
        assert '<?xml versio...DEXING></NML>' == '<?xml versio...DEXING></NML>'

          Skipping 305 identical leading characters in diff, use -v to show
          -  BITRATE="320000" PLAYTIME_FLOAT="100.0" FILESIZE="8192"></INFO></ENTRY></COLLECTION><PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS><SETS></SETS><INDEXING></INDEXING></NML>
          ?           ^^^^^^^
          +  BITRATE="1411000" PLAYTIME_FLOAT="100.0" FILESIZE="8192"></INFO></ENTRY></COLLECTION><PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS><SETS></SETS><INDEXING></INDEXING></NML>
          ?           ^^^^^^^^
    """
    inputs = _tier_pair({"bitrate": ("320000", "1411000")})
    plain = assemble_output(*inputs, MatchConfidence.STRICT)
    named = assemble_output(
        *inputs, MatchConfidence.STRICT, resolutions={_TIER_KEY: (1, _TIER_KEY)}
    )
    assert plain.output is not None
    assert named.output == plain.output
    assert named.settled_rows == plain.settled_rows
    assert named.conflict_rows == []


def test_resolved_conflicts_carries_settled_rows_by_name() -> None:
    """_resolve_conflicts returns the settled rows as a named attribute
    beside entry_patches, so the five values a positional caller unpacks
    stay the five it unpacks and assemble_output reads an attribute that
    exists (DL-100's precedent, DL-104).

    Mutation: `self.settled_rows = settled_rows` in
    ResolvedConflicts.__new__ replaced by `self.settled_rows = []`.
    Observed:
        ValueError: not enough values to unpack (expected 1, got 0)
    """
    base_text, source_text = _tier_copies({"bitrate": ("320000", "1411000")})
    resolved = _resolved_groups(base_text, [source_text])
    old_to_new_key, conflict_rows, unresolved, new_entries, ambiguous_keys = resolved
    assert conflict_rows == []
    assert unresolved is False
    (settled,) = resolved.settled_rows
    assert settled.identity_key == _TIER_KEY
    assert resolved.entry_patches == []


def test_tracked_attrs_is_metadata_tiers_tuple() -> None:
    """splice holds no second tuple of the six names: answer_detail's
    import of _TRACKED_ATTRS and every test reading it reach the one
    definition the tier is decided on (DL-326).

    Mutation: _TRACKED_ATTRS spelled out in splice.py again as its
    own six-name tuple instead of metadata_tier.TRACKED_ATTRS.
    Observed:
        AssertionError: assert ('artist', 'title', 'album', 'filesize', 'playtime_float', 'bitrate') is ('artist', 'title', 'album', 'filesize', 'playtime_float', 'bitrate')
         +  where ('artist', 'title', 'album', 'filesize', 'playtime_float', 'bitrate') = <module 'traktor_nml.metadata_tier' from 'C:\\codex\\traktor-nml-tool\\traktor_nml\\metadata_tier.py'>.TRACKED_ATTRS
    """
    from traktor_nml import metadata_tier

    assert _TRACKED_ATTRS is metadata_tier.TRACKED_ATTRS


def test_the_conflict_csv_and_the_printed_line_stand_for_a_remaining_conflict(
    tmp_path: Path,
) -> None:
    """The three fieldnames and the printed conflict line are what a
    caller of this command already parses, so a group that is still a
    conflict reports exactly what it reported before the tier existed.

    Mutation: a fourth "settled" fieldname added to splice_cmd's
    conflict-report DictWriter.
    Observed:
        AssertionError: assert ['identity_ke...,keep-first,'] == ['identity_ke...t,keep-first']

          At index 0 diff: 'identity_key,attrs,resolution,settled' != 'identity_key,attrs,resolution'
          Use -v to get more diff
    """
    base_text, source_text = _tier_copies({"artist": ("A", "B")})
    base_path = tmp_path / "base.nml"
    base_path.write_text(base_text, encoding="utf-8", newline="")
    other_path = tmp_path / "other.nml"
    other_path.write_text(source_text, encoding="utf-8", newline="")
    csv_path = tmp_path / "conflicts.csv"

    result = run_tool(
        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path),
         "--on-conflict", "keep-first", "--conflict-report", str(csv_path)],
        cwd=tmp_path,
    )

    assert result.exit_code == 0
    assert csv_path.read_text(encoding="utf-8", newline="").splitlines() == [
        "identity_key,attrs,resolution",
        _TIER_KEY + ",artist,keep-first",
    ]
    assert (
        "conflict_key=%s attrs=artist resolution=keep-first" % _TIER_KEY
    ) in result.stdout.splitlines()



def _ET_tostring(element) -> str:
    from traktor_nml.xmlio import ET

    return ET.tostring(element, encoding="unicode")
