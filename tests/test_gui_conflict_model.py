"""Guards for traktor_nml/gui/conflict_model.py's decision states, row
projection, resolutions mapping, candidate re-attachment and write
refusal. Each guard constructs its broken scenario in executable code
and records the mutation applied and the output observed under it,
matching the register tests/test_gui_wizard_state.py uses.

The fixtures build EntryRecords directly and drive splice's own
group_identities and _resolve_conflicts over them, so the identity keys,
the membership and the candidates under test are the ones the merge
itself derives, not a copy of the derivation restated here. Where a
fixture names one source's answer, it names the source at input index 2,
which the run-wide keep-first picker would not choose, so a guard cannot
pass by coinciding with the picker's own answer.
"""

from __future__ import annotations

import inspect

import pytest

from traktor_nml.gui.conflict_model import (
    ALREADY_LISTED,
    IS_A_SOURCE,
    IS_THE_BASE,
    base_refusal,
    source_refusal,
    CONFLICTS_OUTSTANDING,
    CONFLICT_ABORT_TOKEN,
    ConflictDecisions,
    resolve_tally_sentence,
    NO_PREVIEW,
    RUN_REFUSED,
    UNDECIDED,
    candidate_holding_input,
    candidate_reference,
    conflict_groups,
    reference_from_input,
    write_refusal,
    write_refusal_sentence,
)
from traktor_nml.matching import MatchConfidence
from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.splice import (
    ConflictCandidate,
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
    return conflict_groups(conflict_rows)


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


def _three_answer_inputs() -> list[list[EntryRecord]]:
    """A base and two sources disagreeing with each other and with base,
    so the group offers three distinct answers and the one at input index
    2 is not the answer keep-first would name."""
    return _one_track_inputs() + [[_record("/:Two/:", "064")]]


def _agreeing_sources_inputs() -> list[list[EntryRecord]]:
    """A base and two sources that agree with each other and differ from
    base, so the two sources supply one answer between them."""
    return _one_track_inputs() + [[_record("/:Two/:", "128")]]


def _reference_at(group, input_index: int):
    """The candidate reference for the answer the collection at this
    input index supplies."""
    candidate = candidate_holding_input(group.candidates, input_index)
    assert candidate is not None, f"input {input_index} supplies no answer"
    return candidate_reference(candidate)


def test_a_row_projects_the_key_the_attrs_and_the_candidates() -> None:
    """One conflict row carries the identity key, the divergent attribute
    names, one candidate per distinct answer with the records supplying
    it, and the decision.

    Observed with rows() handing the group's member keys through as its
    candidates (`candidates=tuple(sorted(group.member_keys))`):
    AssertionError on `assert row.candidates == groups[0].candidates`,
    reported as `assert ('C:/:Base/:t...e/:track.mp3') ==
    (ConflictCand...rack.mp3'),)))` with `At index 0 diff:
    'C:/:Base/:track.mp3' != ConflictCandidate(values=('320',),
    members=((0, 'C:/:Base/:track.mp3'),))` - the row named the records
    without naming what any of them answered.
    """
    groups = _groups(_one_track_inputs())
    decisions = ConflictDecisions()

    rows = decisions.rows(groups)

    assert len(rows) == 1
    row = rows[0]
    assert row.identity_key == "C:/:Base/:track.mp3"
    assert row.attrs == ("bitrate",)
    assert row.candidates == groups[0].candidates
    assert len(row.candidates) == 2
    assert [candidate.values for candidate in row.candidates] == [("320",), ("128",)]
    assert [candidate.members for candidate in row.candidates] == [
        ((0, "C:/:Base/:track.mp3"),),
        ((1, "C:/:One/:track.mp3"),),
    ]
    assert row.decision == UNDECIDED


def test_two_agreeing_sources_present_one_answer_and_three_disagreeing_present_three() -> None:
    """Candidates are one per distinct answer, not one per record: two
    sources agreeing with each other collapse into one candidate naming
    both, while three disagreeing records present three (DL-150).

    Observed with splice._candidates keyed by the contributor as well as
    the values (`grouped.setdefault(values + (str(input_idx),), ...)`,
    reverted after the run): AssertionError on `assert
    len(agreeing.candidates) == 2`, reported as `assert 3 == 2`, the
    three being `ConflictCandidate(values=('320', '0'), members=((0,
    'C:/:Base/:track.mp3'),))`, `ConflictCandidate(values=('128', '1'),
    members=((1, 'C:/:One/:track.mp3'),))` and
    `ConflictCandidate(values=('128', '2'), members=((2,
    'C:/:Two/:track.mp3'),))` - the two agreeing sources presented the
    operator two buttons for one answer.
    """
    agreeing = _groups(_agreeing_sources_inputs())[0]
    distinct = _groups(_three_answer_inputs())[0]

    assert len(agreeing.candidates) == 2
    assert [candidate.values for candidate in agreeing.candidates] == [("320",), ("128",)]
    agreed = candidate_holding_input(agreeing.candidates, 1)
    assert agreed is not None
    assert agreed.members == (
        (1, "C:/:One/:track.mp3"),
        (2, "C:/:Two/:track.mp3"),
    )
    assert candidate_holding_input(agreeing.candidates, 2) is agreed

    assert len(distinct.candidates) == 3
    assert [candidate.values for candidate in distinct.candidates] == [
        ("320",),
        ("128",),
        ("064",),
    ]
    assert [len(candidate.members) for candidate in distinct.candidates] == [1, 1, 1]


def test_a_fresh_set_reports_every_key_undecided_and_counts_them_outstanding() -> None:
    """A fresh decision set reads every group undecided and its
    outstanding count equals the number of conflict rows.

    Observed with decision returning a fabricated reference in place of
    UNDECIDED for an unheld key (`return (0, group.identity_key)` under
    `if held is None:`): AssertionError on `assert
    [decisions.decision(group) for group in groups] == [UNDECIDED,
    UNDECIDED]`, reported as `assert [(0, 'C:/:Bas.../:other.mp3')] ==
    ['undecided', 'undecided']` with `At index 0 diff: (0,
    'C:/:Base/:track.mp3') != 'undecided'`.
    """
    groups = _groups(_two_track_inputs())
    decisions = ConflictDecisions()

    assert len(groups) == 2
    assert [decisions.decision(group) for group in groups] == [UNDECIDED, UNDECIDED]
    assert decisions.outstanding(groups) == len(groups)


def test_resolving_to_one_answer_reads_that_answer_back() -> None:
    """resolve sets one key and decision reads that same answer's
    reference back, for an answer the run-wide picker would not name.

    Observed with resolve storing the group's first candidate in place of
    the one the reference names (`candidate_reference(
    group.candidates[0])` in the store): AssertionError on `assert
    decisions.decision(group) == (2, "C:/:Two/:track.mp3")`, reported as
    `assert (0, 'C:/:Base/:track.mp3') == (2, 'C:/:Two/:track.mp3')` with
    `At index 0 diff: 0 != 2` - every pick read back as base's own
    answer.
    """
    group = _groups(_three_answer_inputs())[0]
    decisions = ConflictDecisions()

    decisions.resolve(group, _reference_at(group, 0))
    assert decisions.decision(group) == (0, "C:/:Base/:track.mp3")

    decisions.resolve(group, _reference_at(group, 2))
    assert decisions.decision(group) == (2, "C:/:Two/:track.mp3")
    assert decisions.decision(group) != _reference_at(group, 1)


def test_a_pick_names_the_lowest_contributor_of_the_answer_it_settles() -> None:
    """Where two collections supply one answer, naming either records the
    same pair - the contributor of lowest input index - so the recorded
    value does not depend on which button was pressed (DL-150).

    Observed with candidate_reference answering the last contributor
    (`return candidate.members[-1]`): AssertionError on `assert
    by_second == (1, "C:/:One/:track.mp3")`, reported as `assert (2,
    'C:/:Two/:track.mp3') == (1, 'C:/:One/:track.mp3')` with `At index 0
    diff: 2 != 1` - the two buttons for one answer recorded two different
    picks.
    """
    group = _groups(_agreeing_sources_inputs())[0]

    first = ConflictDecisions()
    first.resolve(group, (1, "C:/:One/:track.mp3"))
    by_second = first.decision(group)

    second = ConflictDecisions()
    second.resolve(group, (2, "C:/:Two/:track.mp3"))
    by_third = second.decision(group)

    assert by_second == by_third
    assert by_second == (1, "C:/:One/:track.mp3")


def test_a_reference_naming_no_candidate_of_the_group_is_refused() -> None:
    """resolve accepts only a pair one of the group's own candidates
    carries. A pair naming a record of another group, or a record at an
    input the group holds nothing from, is a programming error in the
    caller rather than stale operator input (DL-159).

    Observed with resolve's refusal replaced by storing the reference as
    given (`self._decisions[group.identity_key] = _Decision(
    tuple(reference), group.member_keys, group.candidates)` in place of
    the `raise ValueError(...)`): `Failed: DID NOT RAISE <class
    'ValueError'>` at the first `with pytest.raises(ValueError):` - the
    pair (7, 'C:/:Nowhere/:track.mp3') was stored as a pick, and
    resolutions would then emit it to the core.
    """
    group = _groups(_three_answer_inputs())[0]
    decisions = ConflictDecisions()

    with pytest.raises(ValueError):
        decisions.resolve(group, (7, "C:/:Nowhere/:track.mp3"))

    # The primary key is one a candidate carries; the input index is not.
    with pytest.raises(ValueError):
        decisions.resolve(group, (5, "C:/:Two/:track.mp3"))

    assert decisions.decision(group) == UNDECIDED
    assert decisions.resolutions([group]) == {}


def test_a_fresh_set_and_one_reset_key_by_key_behave_identically() -> None:
    """Resetting every decided key reads back exactly what a fresh set
    reads - the same rows, the same outstanding count and the same
    (empty) resolutions mapping.

    Observed with reset's body replaced by `pass`, so a decided key
    survives the reset: AssertionError on `assert decisions.rows(groups)
    == fresh_rows`, reported with `At index 0 diff:
    ConflictRowView(identity_key='C:/:Base/:track.mp3',
    attrs=('bitrate',), candidates=(ConflictCandidate(values=('320',),
    members=((0, 'C:/:Base/:track.mp3'),)),
    ConflictCandidate(values=('128',), members=((1,
    'C:/:One/:track.mp3'),))), decision=(0, 'C:/:Base/:track.mp3')) !=
    ConflictRowView(... decision='undecided')`.
    """
    groups = _groups(_two_track_inputs())
    fresh = ConflictDecisions()
    fresh_rows = fresh.rows(groups)

    decisions = ConflictDecisions()
    decisions.resolve(groups[0], _reference_at(groups[0], 0))
    decisions.resolve(groups[1], _reference_at(groups[1], 1))
    for group in groups:
        decisions.reset(group.identity_key)

    assert decisions.rows(groups) == fresh_rows
    assert decisions.outstanding(groups) == fresh.outstanding(groups)
    assert decisions.resolutions(groups) == {}


def test_a_bulk_action_leaves_an_explicit_pick_standing() -> None:
    """resolve_where_answered settles every undecided group its predicate answers
    for and leaves a group already decided another way standing.

    Observed with resolve_where_answered's guard dropped (the `if self.decision(
    group) != UNDECIDED: continue` lines removed, so it resolves every
    group): AssertionError on `assert decisions.decision(picked) ==
    picked_reference`, reported as `assert (0, 'C:/:Base/:track.mp3') ==
    (1, 'C:/:One/:track.mp3')` with `At index 0 diff: 0 != 1` - the
    explicit pick on the source's answer was overwritten by the bulk
    action for base.
    """
    groups = _groups(_two_track_inputs())
    picked, other = groups[0], groups[1]
    picked_reference = _reference_at(picked, 1)

    decisions = ConflictDecisions()
    decisions.resolve(picked, picked_reference)
    decisions.resolve_where_answered(groups, reference_from_input(0))

    assert decisions.decision(picked) == picked_reference
    assert decisions.decision(other) == _reference_at(other, 0)
    assert decisions.outstanding(groups) == 0


def test_a_bulk_action_leaves_a_group_its_collection_has_no_record_in_undecided() -> None:
    """A bulk action for one collection settles the groups that
    collection holds a record in and leaves every other group undecided
    and counted by outstanding, rather than folding someone else's answer
    into a row the collection said nothing about (DL-154).

    Observed with reference_from_input's predicate falling back to the
    group's first candidate (`return candidate_reference(candidate if
    candidate is not None else candidates[0])`): AssertionError on
    `assert decisions.decision(untouched) == UNDECIDED`, reported as
    `assert (0, 'C:/:Base/:track.mp3') == 'undecided'` - a bulk action
    for the third collection settled a group that collection holds no
    record in, on base's own answer.
    """
    inputs = [
        [
            _record("/:Base/:", "320"),
            _record("/:Base/:", "320", title="Other", file_name="other.mp3", playtime="200.0"),
        ],
        [
            _record("/:One/:", "128"),
            _record("/:One/:", "128", title="Other", file_name="other.mp3", playtime="200.0"),
        ],
        [_record("/:Two/:", "064", title="Other", file_name="other.mp3", playtime="200.0")],
    ]
    groups = _groups(inputs)
    held = {group.identity_key: group for group in groups}
    covered = held["C:/:Base/:other.mp3"]
    untouched = held["C:/:Base/:track.mp3"]

    decisions = ConflictDecisions()
    decisions.resolve_where_answered(groups, reference_from_input(2))

    assert candidate_holding_input(untouched.candidates, 2) is None
    assert decisions.decision(covered) == (2, "C:/:Two/:other.mp3")
    assert decisions.decision(untouched) == UNDECIDED
    assert decisions.outstanding(groups) == 1
    assert set(decisions.resolutions(groups)) == {"C:/:Base/:other.mp3"}


def test_the_resolutions_mapping_carries_pairs_and_omits_undecided_keys() -> None:
    """The mapping handed to the core carries an (input index, primary
    key) pair per decided key; an undecided key is absent from it
    entirely rather than carrying a token.

    Observed with resolutions' guard dropped (`mapping[
    group.identity_key] = decision` written unconditionally):
    AssertionError on `assert mapping == {decided.identity_key: (1,
    "C:/:One/:track.mp3")}`, reported with `Left contains 1 more item:
    {'C:/:Base/:other.mp3': 'undecided'}` - the undecided key reached the
    mapping carrying a token _resolve_conflicts cannot read as a pair.
    """
    groups = _groups(_two_track_inputs())
    decided, undecided = groups[0], groups[1]

    decisions = ConflictDecisions()
    decisions.resolve(decided, _reference_at(decided, 1))

    mapping = decisions.resolutions(groups)

    assert mapping == {decided.identity_key: (1, "C:/:One/:track.mp3")}
    assert undecided.identity_key not in mapping
    assert all(
        isinstance(value, tuple)
        and len(value) == 2
        and isinstance(value[0], int)
        and isinstance(value[1], str)
        for value in mapping.values()
    )


def test_a_vanished_key_contributes_nothing_to_the_resolutions_mapping() -> None:
    """A decision made against a key the current conflict rows do not
    name contributes nothing: a second run whose source no longer holds
    the track reports no group for that key.

    Observed with resolutions iterating self._decisions in place of the
    groups passed in (`for key, held in self._decisions.items():
    mapping[key] = held.reference`): AssertionError on `assert
    set(decisions.resolutions(second)) == {group.identity_key for group
    in second}`, reported with `Extra items in the left set:
    'C:/:Base/:track.mp3'` - the mapping named a group the second run has
    no row for.
    """
    first = _groups(_two_track_inputs())
    decisions = ConflictDecisions()
    for group in first:
        decisions.resolve(group, _reference_at(group, 1))

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


def test_a_decision_re_attaches_when_the_membership_and_the_answers_are_unchanged() -> None:
    """A decision stands across a second conflict-row list built from the
    same inputs: the identity key names a group whose member primary keys
    are the identical set and whose candidates are the identical tuple.

    Observed with decision comparing the held candidates to the group's
    attrs (`held.candidates != group.attrs`): AssertionError on `assert
    second_decisions == [reference]`, reported as `assert ['undecided']
    == [(1, 'C:/:One/:track.mp3')]` with `At index 0 diff: 'undecided' !=
    (1, 'C:/:One/:track.mp3')` - a tuple of candidates never equals a
    tuple of attribute names, so no decision would survive a re-preview.
    """
    first = _groups(_one_track_inputs())
    decisions = ConflictDecisions()
    reference = _reference_at(first[0], 1)
    decisions.resolve(first[0], reference)

    second = _groups(_one_track_inputs())

    assert second[0].member_keys == first[0].member_keys
    assert second[0].candidates == first[0].candidates
    second_decisions = [decisions.decision(group) for group in second]
    assert second_decisions == [reference]
    assert decisions.outstanding(second) == 0
    assert decisions.resolutions(second) == {"C:/:Base/:track.mp3": (1, "C:/:One/:track.mp3")}


def _enlarged_inputs() -> list[list[EntryRecord]]:
    """The one-track inputs with a second source holding a third copy of
    the same track at its own path: the union-find pulls it into the same
    group, so the identity key is unchanged and the member set has
    grown."""
    return _one_track_inputs() + [[_record("/:Two/:", "192")]]


def test_a_group_an_added_source_enlarged_returns_to_undecided() -> None:
    """A decision whose group an added source enlarged reads back
    undecided and raises the outstanding count, even though the identity
    key is unchanged (DL-115).

    Observed with decision trusting the key alone (the `if
    held.member_keys != group.member_keys or held.candidates !=
    group.candidates: return UNDECIDED` lines deleted): AssertionError on
    `assert decisions.decision(enlarged[0]) == UNDECIDED`, reported as
    `assert (1, 'C:/:One/:track.mp3') == 'undecided'` - a pick made
    against two records read back as standing over three.
    """
    first = _groups(_one_track_inputs())
    decisions = ConflictDecisions()
    decisions.resolve(first[0], _reference_at(first[0], 1))

    enlarged = _groups(_enlarged_inputs())

    assert enlarged[0].identity_key == first[0].identity_key
    assert enlarged[0].member_keys != first[0].member_keys
    assert decisions.decision(enlarged[0]) == UNDECIDED
    assert decisions.outstanding(enlarged) == 1
    assert decisions.resolutions(enlarged) == {}


def _same_path_inputs() -> list[list[EntryRecord]]:
    """A base and one source holding one file at ONE location, so both
    records carry the identical primary key (DL-004)."""
    return [[_record("/:Music/:", "320")], [_record("/:Music/:", "128")]]


def _same_path_with_second_source() -> list[list[EntryRecord]]:
    """The same file again from a third collection at that same location:
    the added record's primary key is the one the group already holds, so
    member_keys cannot see the addition and only the answers change."""
    return _same_path_inputs() + [[_record("/:Music/:", "064")]]


def test_a_source_added_at_an_existing_members_path_returns_the_pick_to_undecided() -> None:
    """A source added at a location an existing member already holds
    leaves member_keys IDENTICAL while adding an answer, and the held
    pick reads back undecided because re-attachment compares the
    candidate set too (DL-158).

    Observed with decision comparing member_keys alone (`if
    held.member_keys != group.member_keys: return UNDECIDED`, dropping
    the candidate comparison - the rule shipped at aa6ab76):
    AssertionError on `assert decisions.decision(after) == UNDECIDED`,
    reported as `assert (1, 'C:/:Music/:track.mp3') == 'undecided'`, the
    group printing `member_keys=frozenset({'C:/:Music/:track.mp3'})` and
    three candidates - the pick made when two answers were on offer stood
    while three were, and the write would have proceeded over an answer
    set the operator never saw.
    """
    before = _groups(_same_path_inputs())[0]
    decisions = ConflictDecisions()
    decisions.resolve(before, _reference_at(before, 1))

    after = _groups(_same_path_with_second_source())[0]

    # The measurement this guard exists for: the membership is blind to
    # the addition, the answers are not.
    assert after.identity_key == before.identity_key
    assert after.member_keys == before.member_keys == frozenset({"C:/:Music/:track.mp3"})
    assert len(before.candidates) == 2
    assert len(after.candidates) == 3
    assert after.candidates[:2] == before.candidates
    assert after.candidates[2].members == ((2, "C:/:Music/:track.mp3"),)

    assert decisions.decision(after) == UNDECIDED
    assert decisions.outstanding([after]) == 1
    assert decisions.resolutions([after]) == {}


def test_an_added_source_leaves_the_picks_on_the_groups_it_does_not_reach_standing() -> None:
    """The widened comparison fires per group, not per re-preview: a
    source added to one group leaves every group it holds no record in
    carrying the same membership and the same answers, so those picks
    stand and only the group whose answers changed returns to undecided
    (R-005).

    Observed with decision comparing every held pick's candidates rather
    than this group's (`any(other.candidates != group.candidates for
    other in self._decisions.values())` in place of `held.candidates !=
    group.candidates`), so one changed row unsettles the rest:
    AssertionError on `assert decisions.decision(untouched) == (1,
    "C:/:One/:track.mp3")`, reported as `assert 'undecided' == (1,
    'C:/:One/:track.mp3')` - a re-preview reaching one group sent the
    operator back to a row it never touched.
    """
    before = _groups(_two_track_inputs())
    decisions = ConflictDecisions()
    for group in before:
        decisions.resolve(group, _reference_at(group, 1))

    added = _two_track_inputs() + [
        [_record("/:Two/:", "064", title="Other", file_name="other.mp3", playtime="200.0")]
    ]
    after = {group.identity_key: group for group in _groups(added)}
    untouched = after["C:/:Base/:track.mp3"]
    reached = after["C:/:Base/:other.mp3"]

    assert untouched.candidates == before[0].candidates
    assert len(reached.candidates) == 3
    assert decisions.decision(untouched) == (1, "C:/:One/:track.mp3")
    assert decisions.decision(reached) == UNDECIDED
    assert decisions.outstanding(list(after.values())) == 1


def test_a_re_preview_after_an_added_source_refuses_the_write() -> None:
    """The re-preview after an added source enlarges a decided group runs
    with an empty resolutions mapping, so it aborts, and the refusal
    names the one conflict outstanding rather than a write proceeding.

    Observed with decision trusting the key alone (the `if
    held.member_keys != group.member_keys or held.candidates !=
    group.candidates: return UNDECIDED` lines deleted): AssertionError on
    `assert unresolved is True`, reported as `assert False is True` - the
    stale pick reached the resolutions mapping and settled the enlarged
    group, so the re-preview did not abort at all and a winner nobody
    chose for the third copy would have been written.
    """
    first = _groups(_one_track_inputs())
    decisions = ConflictDecisions()
    decisions.resolve(first[0], _reference_at(first[0], 1))

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
    decisions.resolve(groups[0], _reference_at(groups[0], 1))

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


def test_the_conflict_refusal_names_choosing_a_collection_per_row() -> None:
    """The refusal sentence names the control the row actually renders -
    one per answer, each naming the collections that supply it - so it
    tells the operator to choose a collection for each row rather than
    naming two sides the page does not offer (DL-160).

    Observed with the sentence's second clause reading `Choose base or
    source for each row above, then run Preview again.`: AssertionError
    on `assert "collection" in sentence`, reported as `assert
    'collection' in 'The preview refused: 1 conflict(s) still to decide.
    Choose base or source for each row above, then run Preview again.'` -
    the sentence named a two-sided control over a row offering three.
    """
    groups = _groups(_three_answer_inputs())
    decisions = ConflictDecisions()
    result = SpliceResult(output=None, stats={}, errors=["unresolved_conflicts"])

    refusal = write_refusal(result, decisions, groups)
    assert refusal is not None
    sentence = write_refusal_sentence(refusal)

    # The row renders one control per candidate, three here, so no
    # sentence naming two sides describes it.
    assert len(groups[0].candidates) == 3
    assert "collection" in sentence
    assert "base or source" not in sentence
    assert "Preview" in sentence


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


def test_a_group_is_projected_from_the_row_alone_with_no_records_given() -> None:
    """conflict_groups is handed the run's rows and nothing else: a row
    carrying its membership and its candidates yields the group the page
    shows, with no collection records and no MatchConfidence anywhere in
    the call, so the page cannot regroup under a rule that drifts from
    the run's.

    Observed with conflict_groups' signature widened to `(conflict_rows,
    records_by_input=None, confidence=None)`: AssertionError on `assert
    list(inspect.signature(conflict_groups).parameters) ==
    ["conflict_rows"]`, reported as `assert ['conflict_ro...
    'confidence'] == ['conflict_rows']` with `Left contains 2 more items,
    first extra item: 'records_by_input'`.

    Observed with `candidates=row.candidates` replaced by
    `candidates=tuple(c.values for c in row.candidates)`: AssertionError
    on `assert group.candidates == row.candidates`, reported as `assert
    (('16', '320'), ('32', '128')) == (ConflictCand...track.mp3'))))`
    with `At index 0 diff: ('16', '320') !=
    ConflictCandidate(values=('16', '320'), members=((0,
    'C:/:Base/:track.mp3'),))` - the answers reached the page with
    nothing saying which collection supplied them.
    """
    row = ConflictRow(
        "C:/:Base/:track.mp3",
        "filesize,bitrate",
        "unresolved",
        member_keys=frozenset({"C:/:Base/:track.mp3", "C:/:One/:track.mp3"}),
        candidates=(
            ConflictCandidate(("16", "320"), ((0, "C:/:Base/:track.mp3"),)),
            ConflictCandidate(
                ("32", "128"),
                ((1, "C:/:One/:track.mp3"), (2, "C:/:Two/:track.mp3")),
            ),
        ),
    )

    assert list(inspect.signature(conflict_groups).parameters) == ["conflict_rows"]
    groups = conflict_groups([row])

    assert len(groups) == 1
    group = groups[0]
    assert group.identity_key == "C:/:Base/:track.mp3"
    assert group.attrs == ("filesize", "bitrate")
    assert group.member_keys == frozenset(
        {"C:/:Base/:track.mp3", "C:/:One/:track.mp3"}
    )
    assert group.candidates == row.candidates
    assert len(group.candidates) == 2
    assert candidate_reference(group.candidates[1]) == (1, "C:/:One/:track.mp3")


def test_a_row_naming_no_membership_names_no_group() -> None:
    """A row carrying no member keys names no identity group a per-key
    resolution could settle, so it is left out rather than yielding a
    group whose empty member set no re-attachment could ever match.

    Observed with `if not row.member_keys or row.identity_key in seen:`
    reduced to `if row.identity_key in seen:`: AssertionError on `assert
    conflict_groups([rootless]) == []`, reported as `assert
    [ConflictGrou...andidates=())] == []` with `Left contains one more
    item: ConflictGroup(identity_key='C:/:Base/:track.mp3',
    attrs=('bitrate',), member_keys=frozenset(), candidates=())`.
    """
    rootless = ConflictRow("C:/:Base/:track.mp3", "bitrate", "unresolved")

    assert conflict_groups([rootless]) == []


def test_a_non_metadata_row_names_no_conflict_group() -> None:
    """A row reporting a duplicate playlist name carries a literal in
    place of a divergent attribute list, and names no group a per-key
    resolution can settle, so conflict_groups leaves it out even where
    its key collides with a real identity group's.

    Observed with conflict_groups' `if row.attrs in
    NON_METADATA_ROW_ATTRS: continue` deleted: AssertionError on `assert
    conflict_groups([colliding]) == []`, reported as `assert
    [ConflictGrou...andidates=())] == []` with `Left contains one more
    item: ConflictGroup(identity_key='C:/:Base/:track.mp3',
    attrs=('playlist_name',), member_keys=frozenset({'C:/:One/:track.mp3',
    'C:/:Base/:track.mp3'}), candidates=())` - the literal was named as a
    divergent attribute of a real group.
    """
    records_by_input = _one_track_inputs()
    identities = group_identities(records_by_input, MatchConfidence.STRICT)
    members = next(
        m for m in identities.values() if len({idx for idx, _ in m}) > 1
    )
    colliding = ConflictRow(
        group_identity_key(members),
        "playlist_name",
        "ambiguous",
        member_keys=frozenset(record.primary_key for _, record in members),
    )

    assert conflict_groups([colliding]) == []


def test_a_collection_already_listed_is_refused(tmp_path) -> None:
    """A candidate naming a collection the source list already holds is
    refused, so one file cannot be folded twice.

    Observed with source_refusal's `if any(_same_file(candidate,
    listed) for listed in sources): return ALREADY_LISTED` branch
    deleted: `AssertionError: assert None == 'already_listed'`, the
    candidate naming the one path already in the list.
    """
    listed = tmp_path / "source.nml"
    listed.write_text("<NML/>", encoding="utf-8")
    base = tmp_path / "base.nml"
    base.write_text("<NML/>", encoding="utf-8")

    assert source_refusal(listed, base, [listed]) == ALREADY_LISTED


def test_the_collection_being_repaired_is_refused_as_a_source(tmp_path) -> None:
    """A candidate naming the collection being repaired is refused, so a
    run cannot take playlists from the collection it repairs.

    Observed with source_refusal's `if base_path is not None and
    _same_file(candidate, base_path): return IS_THE_BASE` branch
    deleted: `AssertionError: assert None == 'is_the_base'`, the
    candidate and base_path naming one file.
    """
    base = tmp_path / "base.nml"
    base.write_text("<NML/>", encoding="utf-8")

    assert source_refusal(base, base, []) == IS_THE_BASE


def test_a_collection_on_neither_side_is_accepted(tmp_path) -> None:
    """A candidate naming no collection the page already holds is
    accepted, so the refusal answers only the collisions it names.

    Observed with `return ALREADY_LISTED` inserted as source_refusal's
    first statement: `AssertionError: assert 'already_listed' is None`,
    a candidate on neither side refused anyway.
    """
    base = tmp_path / "base.nml"
    base.write_text("<NML/>", encoding="utf-8")
    listed = tmp_path / "one.nml"
    listed.write_text("<NML/>", encoding="utf-8")
    fresh = tmp_path / "two.nml"
    fresh.write_text("<NML/>", encoding="utf-8")

    assert source_refusal(fresh, base, [listed]) is None


def test_a_source_is_refused_as_the_collection_to_repair(tmp_path) -> None:
    """The same collision read from the other side: a candidate the source
    list already holds is refused as the collection to repair.

    Observed with base_refusal's `if any(_same_file(candidate, listed)
    for listed in sources): return IS_A_SOURCE` branch deleted:
    `AssertionError: assert None == 'is_a_source'`.
    """
    listed = tmp_path / "source.nml"
    listed.write_text("<NML/>", encoding="utf-8")

    assert base_refusal(listed, [listed]) == IS_A_SOURCE


def test_two_paths_naming_one_file_are_one_collection(tmp_path) -> None:
    """Paths are compared resolved, so a path through a parent directory
    and the plain path name one collection rather than two.

    Observed with `_same_file(candidate, listed)` replaced by
    `candidate is listed`: `AssertionError: assert None ==
    'already_listed'`, the path reading `sub/../source.nml` read as a
    second collection beside `source.nml`.
    """
    listed = tmp_path / "source.nml"
    listed.write_text("<NML/>", encoding="utf-8")
    base = tmp_path / "base.nml"
    base.write_text("<NML/>", encoding="utf-8")
    roundabout = tmp_path / "sub" / ".." / "source.nml"
    (tmp_path / "sub").mkdir()

    assert source_refusal(roundabout, base, [listed]) == ALREADY_LISTED


def test_a_non_conflict_abort_is_not_read_as_outstanding_conflicts() -> None:
    """A run that aborted on something other than conflicts is not read as
    a conflict refusal, and its sentence sends the operator to the step
    that lists the run's own reasons rather than printing a conflict
    count.

    The reasons themselves stay on the refusal, where the preview step
    reads them: the sentence names how many there are and where to see
    them, because a toast reciting one machine token and leaving the rest
    unmentioned is a message the operator cannot act on (DL-229).

    assemble_output aborts on many things besides unresolved conflicts -
    a location collision among them - and a refusal keyed on `output is
    None` alone renders every one of them to the operator as a conflict
    count, usually "0 conflict(s) still to decide".

    Observed with write_refusal's token test in conflict_model.py
    replaced by `if True:`, so every abort takes the conflict branch:
    AssertionError on `assert refusal.reason == RUN_REFUSED`, reported as
    `assert 'conflicts_outstanding' == 'run_refused'` - a location
    collision answered as outstanding conflicts. conflict_model.py was
    restored from a copy taken beforehand, never via `git checkout`, and
    re-running confirmed it passes.
    """
    groups = _groups(_two_track_inputs())
    decisions = ConflictDecisions()
    result = SpliceResult(
        output=None,
        stats={},
        errors=["entry_location_collision key=C:/:Music/:x.mp3"],
    )

    refusal = write_refusal(result, decisions, groups)
    assert refusal is not None
    assert refusal.reason == RUN_REFUSED
    assert refusal.reason != CONFLICTS_OUTSTANDING
    assert refusal.outstanding is None
    assert refusal.errors == ("entry_location_collision key=C:/:Music/:x.mp3",)

    sentence = write_refusal_sentence(refusal)
    assert "conflict(s) still to decide" not in sentence
    assert "1 reason" in sentence, sentence
    assert "Back to the preview" in sentence, sentence


def test_the_conflict_abort_still_answers_outstanding_conflicts() -> None:
    """The conflict abort itself still answers CONFLICTS_OUTSTANDING with
    the count of undecided rows: reading the errors narrows which aborts
    take that branch and must not take the conflict abort out of it.

    Observed with write_refusal's token test in conflict_model.py
    replaced by `if False:`, so no abort reaches the conflict branch:
    AssertionError on `assert refusal.reason == CONFLICTS_OUTSTANDING`,
    reported as `assert 'run_refused' == 'conflicts_outstanding'` - the
    conflict abort lost its count and its sentence. conflict_model.py was
    restored from a copy taken beforehand, never via `git checkout`, and
    re-running confirmed it passes.
    """
    groups = _groups(_two_track_inputs())
    decisions = ConflictDecisions()
    result = SpliceResult(output=None, stats={}, errors=[CONFLICT_ABORT_TOKEN])

    refusal = write_refusal(result, decisions, groups)
    assert refusal is not None
    assert refusal.reason == CONFLICTS_OUTSTANDING
    assert refusal.outstanding == len(groups)
    assert refusal.errors == ()
    assert f"{len(groups)} conflict(s) still to decide" in write_refusal_sentence(refusal)


def test_the_resolve_tally_agrees_with_the_count_it_names():
    """A run whose collections diverge over one track is the ordinary
    case, and the strip above the table reads its noun off that count
    rather than assuming more than one (DL-233).

    Mutation: the ternary in conflict_model.resolve_tally_sentence
    replaced by the plural alone, `tracks = "tracks carry"`. Observed,
    which is what the served page read before the correction:
        E       AssertionError: assert '1 tracks car...ided, 1 to go' == '1 track carr...ided, 1 to go'
        E         - 1 track carries more than one answer - 0 decided, 1 to go
        E         + 1 tracks carry more than one answer - 0 decided, 1 to go
    """
    one = resolve_tally_sentence(1, 0, 1)
    assert one == "1 track carries more than one answer - 0 decided, 1 to go"
    many = resolve_tally_sentence(34, 34, 0)
    assert many == "34 tracks carry more than one answer - 34 decided, 0 to go"
