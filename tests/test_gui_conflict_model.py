"""Guards for traktor_nml/gui/conflict_model.py's decision states, row
projection, resolutions mapping, membership re-attachment and write
refusal. Each guard constructs its broken scenario in executable code
and records the mutation applied and the output observed under it,
matching the register tests/test_gui_wizard_state.py uses.

The fixtures build EntryRecords directly and drive splice's own
group_identities and _resolve_conflicts over them, so the identity keys
and the membership under test are the ones the merge itself derives, not
a copy of the derivation restated here.
"""

from __future__ import annotations

import pytest

from traktor_nml.gui.conflict_model import (
    BASE,
    CONFLICTS_OUTSTANDING,
    ConflictDecisions,
    NO_PREVIEW,
    SOURCE,
    UNDECIDED,
    conflict_groups,
    write_refusal,
    write_refusal_sentence,
)
from traktor_nml.matching import MatchConfidence
from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.splice import (
    ConflictRow,
    SpliceResult,
    _resolve_conflicts,
    group_identities,
    group_identity_key,
)


def _record(
    dir_value: str,
    bitrate: str = "320",
    title: str = "Song",
    file_name: str = "track.mp3",
    playtime: str = "100.0",
) -> EntryRecord:
    return EntryRecord(
        entry=None,
        artist="A",
        title=title,
        audio_id="",
        filesize="16",
        playtime_float=playtime,
        bitrate=bitrate,
        album="",
        file_name=file_name,
        location=LocationParts(
            volume="C:", volumeid="C:", dir_value=dir_value, file_name=file_name
        ),
    )


def _groups(records_by_input: list[list[EntryRecord]]):
    """The conflict groups a run over these inputs reports, taken off
    splice's own abort path: _resolve_conflicts with on_conflict None
    reports one unresolved ConflictRow per diverging group."""
    identities = group_identities(records_by_input, MatchConfidence.STRICT)
    _mapping, conflict_rows, _unresolved, _new, _ambiguous = _resolve_conflicts(identities, None)
    return conflict_groups(conflict_rows, records_by_input, MatchConfidence.STRICT)


def _one_track_inputs() -> list[list[EntryRecord]]:
    """A base collection and one source holding the same track at a
    differing BITRATE - the smallest input reaching the divergent
    attribute branch."""
    return [[_record("/:Base/:", "320")], [_record("/:One/:", "128")]]


def _two_track_inputs() -> list[list[EntryRecord]]:
    """Two diverging tracks, so bulk resolution has more than one group
    to act over and a mixed decision set is expressible."""
    return [
        [_record("/:Base/:", "320"), _record("/:Base/:", "320", title="Other", file_name="other.mp3", playtime="200.0")],
        [_record("/:One/:", "128"), _record("/:One/:", "128", title="Other", file_name="other.mp3", playtime="200.0")],
    ]


def test_a_row_projects_the_key_the_attrs_and_both_sides_values() -> None:
    """One conflict row carries the identity key, the divergent attribute
    names, the base side's values, the source side's values and the
    decision.

    Observed with conflict_groups' source column fed base_members in
    place of source_members (source_values=_side_values(base_members,
    attrs)): AssertionError on `assert row.source_values == ("128",)`,
    reported as `assert ('320',) == ('128',)` with `At index 0 diff:
    '320' != '128'` - the row read the base side's own BITRATE in its
    source column, so the two columns were indistinguishable.
    """
    groups = _groups(_one_track_inputs())
    decisions = ConflictDecisions()

    rows = decisions.rows(groups)

    assert len(rows) == 1
    row = rows[0]
    assert row.identity_key == "C:/:Base/:track.mp3"
    assert row.attrs == ("bitrate",)
    assert row.base_values == ("320",)
    assert row.source_values == ("128",)
    assert row.decision == UNDECIDED


def test_a_fresh_set_reports_every_key_undecided_and_counts_them_outstanding() -> None:
    """A fresh decision set reads every group undecided and its
    outstanding count equals the number of conflict rows.

    Observed with ConflictDecisions.decision returning BASE in place of
    UNDECIDED for an unheld key (`return BASE` under `if held is None or
    held.member_keys != group.member_keys:`): AssertionError on the
    decision list, reported as `assert ['base', 'base'] == ['undecided',
    'undecided']` with `At index 0 diff: 'base' != 'undecided'`.
    """
    groups = _groups(_two_track_inputs())
    decisions = ConflictDecisions()

    assert len(groups) == 2
    assert [decisions.decision(group) for group in groups] == [UNDECIDED, UNDECIDED]
    assert decisions.outstanding(groups) == len(groups)


def test_resolving_to_base_and_to_source_reads_back() -> None:
    """resolve sets one key and decision reads that same side back.

    Observed with resolve storing the literal BASE in place of the side
    it is passed (`_Decision(BASE, group.member_keys)`): AssertionError
    on `assert decisions.decision(group) == SOURCE`, reported as `assert
    'base' == 'source'` - the source pick read back 'base'.
    """
    groups = _groups(_one_track_inputs())
    group = groups[0]
    decisions = ConflictDecisions()

    decisions.resolve(group, BASE)
    assert decisions.decision(group) == BASE

    decisions.resolve(group, SOURCE)
    assert decisions.decision(group) == SOURCE


def test_an_unknown_side_is_refused() -> None:
    """resolve accepts only base and source; any other token is a
    programming error in the caller.

    Observed with resolve's side check dropped (the `if side not in
    SIDES: raise ValueError(...)` block removed): `Failed: DID NOT RAISE
    <class 'ValueError'>` - the token 'keep-first' was stored as though
    it were a side.
    """
    groups = _groups(_one_track_inputs())
    decisions = ConflictDecisions()

    with pytest.raises(ValueError):
        decisions.resolve(groups[0], "keep-first")


def test_a_fresh_set_and_one_reset_key_by_key_behave_identically() -> None:
    """Resetting every decided key reads back exactly what a fresh set
    reads - the same decisions, the same outstanding count and the same
    (empty) resolutions mapping.

    Observed with reset's body replaced by `pass`, so a decided key
    survives the reset: AssertionError on `assert decisions.rows(groups)
    == fresh_rows`, reported as `At index 0 diff:
    ConflictRowView(identity_key='C:/:Base/:track.mp3',
    attrs=('bitrate',), base_values=('320',), source_values=('128',),
    decision='base') != ConflictRowView(... decision='undecided')`.
    """
    groups = _groups(_two_track_inputs())
    fresh = ConflictDecisions()
    fresh_rows = fresh.rows(groups)

    decisions = ConflictDecisions()
    decisions.resolve(groups[0], BASE)
    decisions.resolve(groups[1], SOURCE)
    for group in groups:
        decisions.reset(group.identity_key)

    assert decisions.rows(groups) == fresh_rows
    assert decisions.outstanding(groups) == fresh.outstanding(groups)
    assert decisions.resolutions(groups) == {}


def test_bulk_all_base_leaves_an_explicit_source_pick_standing() -> None:
    """resolve_all sets every undecided key to one side and leaves a key
    already decided the other way standing, in both directions.

    Observed with resolve_all's guard dropped (the `if self.decision(
    group) == UNDECIDED` test removed, so it resolves every group):
    AssertionError on `assert decisions.decision(picked) == SOURCE`,
    reported as `assert 'base' == 'source'` - the explicit source pick
    was overwritten by the bulk action.
    """
    groups = _groups(_two_track_inputs())
    picked, other = groups[0], groups[1]

    decisions = ConflictDecisions()
    decisions.resolve(picked, SOURCE)
    decisions.resolve_all(groups, BASE)

    assert decisions.decision(picked) == SOURCE
    assert decisions.decision(other) == BASE
    assert decisions.outstanding(groups) == 0

    reverse = ConflictDecisions()
    reverse.resolve(picked, BASE)
    reverse.resolve_all(groups, SOURCE)

    assert reverse.decision(picked) == BASE
    assert reverse.decision(other) == SOURCE


def test_the_resolutions_mapping_omits_undecided_keys() -> None:
    """The mapping handed to the core carries only decided keys; an
    undecided key is absent from it entirely rather than carrying a
    token.

    Observed with resolutions' guard dropped (`mapping[
    group.identity_key] = side` written unconditionally): AssertionError
    on `assert mapping == {decided.identity_key: BASE}`, reported as
    `Left contains 1 more item: {'C:/:Base/:other.mp3': 'undecided'}` -
    the undecided key reached the mapping carrying a token
    _resolve_conflicts does not accept.
    """
    groups = _groups(_two_track_inputs())
    decided, undecided = groups[0], groups[1]

    decisions = ConflictDecisions()
    decisions.resolve(decided, BASE)

    mapping = decisions.resolutions(groups)

    assert mapping == {decided.identity_key: BASE}
    assert undecided.identity_key not in mapping


def test_a_vanished_key_contributes_nothing_to_the_resolutions_mapping() -> None:
    """A decision made against a key the current conflict rows do not
    name contributes nothing: a second run whose source no longer holds
    the track reports no group for that key.

    Observed with resolutions iterating self._decisions in place of the
    groups passed in (`for key, held in self._decisions.items():
    mapping[key] = held.side`): AssertionError on `assert
    set(decisions.resolutions(second)) == {group.identity_key for group
    in second}`, reported as `Extra items in the left set:
    'C:/:Base/:track.mp3'` - the mapping named a group the second run
    has no row for.
    """
    first = _groups(_two_track_inputs())
    decisions = ConflictDecisions()
    for group in first:
        decisions.resolve(group, BASE)

    # The second run's source holds only the second track, so the first
    # track's group is single-input and reports no conflict at all.
    second_inputs = [
        _two_track_inputs()[0],
        [_record("/:One/:", "128", title="Other", file_name="other.mp3", playtime="200.0")],
    ]
    second = _groups(second_inputs)
    vanished = {group.identity_key for group in first} - {group.identity_key for group in second}

    assert vanished == {"C:/:Base/:track.mp3"}
    assert set(decisions.resolutions(second)) == {group.identity_key for group in second}
    assert "C:/:Base/:track.mp3" not in decisions.resolutions(second)


def test_a_decision_re_attaches_when_the_member_set_is_unchanged() -> None:
    """A decision stands across a second conflict-row list built from the
    same inputs: the identity key names a group whose member primary keys
    are the identical set.

    Observed with decision comparing the held member set to the group's
    identity key (`if held is None or held.member_keys != frozenset({
    group.identity_key})`): AssertionError on `assert second_decisions ==
    ["base"]` - the re-attached row read 'undecided', because the held
    set of two member keys never equals the one-element key set, so no
    decision would ever survive a re-preview. Reported as `assert
    ['undecided'] == ['base']`, `At index 0 diff: 'undecided' !=
    'base'`.
    """
    first = _groups(_one_track_inputs())
    decisions = ConflictDecisions()
    decisions.resolve(first[0], BASE)

    second = _groups(_one_track_inputs())

    assert second[0].member_keys == first[0].member_keys
    second_decisions = [decisions.decision(group) for group in second]
    assert second_decisions == [BASE]
    assert decisions.outstanding(second) == 0
    assert decisions.resolutions(second) == {"C:/:Base/:track.mp3": BASE}


def _enlarged_inputs() -> list[list[EntryRecord]]:
    """The one-track inputs with a second source holding a third copy of
    the same track: the union-find pulls it into the same group, so the
    identity key is unchanged and the member set has grown."""
    return _one_track_inputs() + [[_record("/:Two/:", "192")]]


def test_a_group_an_added_source_enlarged_returns_to_undecided() -> None:
    """A decision whose group an added source enlarged reads back
    undecided and raises the outstanding count, even though the identity
    key is unchanged (DL-115).

    Observed with decision trusting the key alone (`if held is None:
    return UNDECIDED; return held.side`, dropping the member_keys
    comparison): AssertionError on `assert decisions.decision(
    enlarged[0]) == UNDECIDED`, reported as `assert 'base' ==
    'undecided'` - a pick made against two records read back as standing
    over three.
    """
    first = _groups(_one_track_inputs())
    decisions = ConflictDecisions()
    decisions.resolve(first[0], BASE)

    enlarged = _groups(_enlarged_inputs())

    assert enlarged[0].identity_key == first[0].identity_key
    assert enlarged[0].member_keys != first[0].member_keys
    assert decisions.decision(enlarged[0]) == UNDECIDED
    assert decisions.outstanding(enlarged) == 1
    assert decisions.resolutions(enlarged) == {}


def test_a_re_preview_after_an_added_source_refuses_the_write() -> None:
    """The re-preview after an added source enlarges a decided group runs
    with an empty resolutions mapping, so it aborts, and the refusal
    names the one conflict outstanding rather than a write proceeding.

    Observed with decision trusting the key alone (`if held is None:
    return UNDECIDED`, dropping the member_keys comparison):
    AssertionError on `assert unresolved is True`, reported as `assert
    False is True` - the stale pick reached the resolutions mapping and
    settled the enlarged group, so the re-preview did not abort at all
    and a winner nobody chose for the third copy would have been
    written.
    """
    first = _groups(_one_track_inputs())
    decisions = ConflictDecisions()
    decisions.resolve(first[0], BASE)

    enlarged_inputs = _enlarged_inputs()
    enlarged = _groups(enlarged_inputs)
    identities = group_identities(enlarged_inputs, MatchConfidence.STRICT)
    _mapping, rows, unresolved, _new, _ambiguous = _resolve_conflicts(
        identities, None, resolutions=decisions.resolutions(enlarged)
    )
    result = SpliceResult(
        output=None,
        stats={},
        conflict_rows=rows,
        errors=["unresolved_conflicts"] if unresolved else [],
    )

    assert unresolved is True
    assert result.output is None
    refusal = write_refusal(result, decisions, enlarged)
    assert refusal is not None
    assert refusal.reason == CONFLICTS_OUTSTANDING
    assert refusal.outstanding == 1
    assert "1 conflict(s) still to decide" in write_refusal_sentence(refusal)


def test_the_refusal_separates_never_previewed_from_refused_with_conflicts() -> None:
    """No preview held and a held preview that refused are two distinct
    reasons, and only the second names the outstanding count.

    Observed with write_refusal's absent-result branch removed (the `if
    result is None: return WriteRefusal(NO_PREVIEW)` lines deleted), so
    an absent result falls through to `result.output`: `AttributeError:
    'NoneType' object has no attribute 'output'` raised at
    conflict_model.py's `if result.output is not None:` - the
    never-previewed state was not a reason at all.
    """
    groups = _groups(_two_track_inputs())
    decisions = ConflictDecisions()
    decisions.resolve(groups[0], BASE)

    never_run = write_refusal(None, decisions, groups)
    assert never_run is not None
    assert never_run.reason == NO_PREVIEW
    assert never_run.outstanding is None
    assert "Run Preview" in write_refusal_sentence(never_run)

    refused = write_refusal(
        SpliceResult(output=None, stats={}, errors=["unresolved_conflicts"]), decisions, groups
    )
    assert refused is not None
    assert refused.reason == CONFLICTS_OUTSTANDING
    assert refused.outstanding == 1
    assert never_run.reason != refused.reason


def test_a_held_preview_carrying_output_yields_no_refusal() -> None:
    """A held result carrying output refuses nothing, whatever the
    decision set holds.

    Observed with write_refusal's output test inverted (`if
    result.output is None: return None`): AssertionError on `assert
    write_refusal(result, decisions, groups) is None`, reported as
    `assert WriteRefusal(reason='conflicts_outstanding', outstanding=2)
    is None` - a preview that wrote output was refused anyway.
    """
    groups = _groups(_two_track_inputs())
    decisions = ConflictDecisions()
    result = SpliceResult(output="<NML/>", stats={}, errors=[])

    assert write_refusal(result, decisions, groups) is None


def test_a_non_metadata_row_names_no_conflict_group() -> None:
    """A row reporting a duplicate playlist name carries a literal in
    place of a divergent attribute list, and names no group a per-key
    resolution can settle, so conflict_groups leaves it out even where
    its key collides with a real identity group's.

    Observed with conflict_groups' `if row.attrs in
    NON_METADATA_ROW_ATTRS: continue` deleted: the row reached
    _side_values with attrs ('playlist_name',) and raised
    `AttributeError: 'EntryRecord' object has no attribute
    'playlist_name'` at conflict_model.py:101 - the literal was read as
    an attribute name off the record.
    """
    records_by_input = _one_track_inputs()
    identities = group_identities(records_by_input, MatchConfidence.STRICT)
    members = next(
        m for m in identities.values() if len({idx for idx, _ in m}) > 1
    )
    colliding = ConflictRow(group_identity_key(members), "playlist_name", "ambiguous")

    assert conflict_groups([colliding], records_by_input, MatchConfidence.STRICT) == []
