"""Guards for the resolve step's own rules in
traktor_nml/gui/conflict_model.py: the gate the footer's sentence and the
advancing control both read, the digit-to-answer lookup Specs' keyboard
map needs, and the two rules a bulk action and a pick already carry, read
through the gate rather than through a count of their own.

Every guard here runs under the system interpreter, which has no nicegui:
conflict_model imports none, which is what puts the resolve step's
decision rules on the side the suite can reach (DL-069, DL-204).

What no guard here holds is that the page reads the gate rather than
counting the undecided groups itself. That reading is an AST walk over
app.py and it lives in
tests/test_gui_conflict_page_controls.py::test_no_decision_arithmetic_is_written_inline,
so the rule and its single call site are held on their own terms.

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation, in the register
tests/test_gui_conflict_model.py uses.
"""

from __future__ import annotations

from traktor_nml.gui import conflict_model
from traktor_nml.splice import ConflictCandidate


def _group(key: str, *answers: tuple[str, tuple[int, ...]]) -> conflict_model.ConflictGroup:
    """One group over `answers`, each an (value, input indices) pair.

    Every member carries `key` as its primary key, which is what a
    location-derived key does for one file held by several collections
    (DL-004, DL-148); the input index is what tells the records apart.
    """
    candidates = tuple(
        ConflictCandidate(
            values=(value,), members=tuple((index, key) for index in indices)
        )
        for value, indices in answers
    )
    return conflict_model.ConflictGroup(
        identity_key=key,
        attrs=("title",),
        member_keys=frozenset({key}),
        candidates=candidates,
    )


def _two_groups() -> list:
    """Two groups: the first held by all three collections, the second by
    the collection being repaired and the source at index 1 alone, so a
    bulk action for index 2 has an answer for one and none for the other.
    """
    return [
        _group("track.mp3", ("Base", (0,)), ("Alpha", (1,)), ("Bravo", (2,))),
        _group("absent.mp3", ("Base", (0,)), ("Alpha", (1,))),
    ]


def test_an_undecided_group_leaves_the_gate_shut_and_names_its_count():
    """One group decided of two reads one outstanding, one decided and a
    shut gate; deciding the second reads zero outstanding, two decided
    and an open gate. The count and the gate come from one walk, so the
    sentence the footer prints and the state of the advancing control
    cannot disagree (DL-204).

    Mutation: resolve_gate's `all_decided=outstanding == 0` was replaced
    with `all_decided=True` in traktor_nml/gui/conflict_model.py and this
    guard rerun. Observed:
        E       AssertionError: one group undecided must shut the gate
        E       assert not True
        E        +  where True = ResolveGate(outstanding=1, decided=1, all_decided=True).all_decided
    """
    groups = _two_groups()
    decisions = conflict_model.ConflictDecisions()
    decisions.resolve(groups[0], (2, "track.mp3"))

    gate = conflict_model.resolve_gate(decisions, groups)
    assert gate.outstanding == 1
    assert gate.decided == 1
    assert not gate.all_decided, "one group undecided must shut the gate"

    decisions.resolve(groups[1], (1, "absent.mp3"))
    settled = conflict_model.resolve_gate(decisions, groups)
    assert settled.outstanding == 0
    assert settled.decided == 2
    assert settled.all_decided


def test_no_groups_at_all_reads_an_open_gate():
    """A run that reported no divergence has nothing to resolve, so the
    gate over an empty group set is open at zero outstanding rather than
    shut on an absent answer.

    Mutation: resolve_gate's `all_decided=outstanding == 0` was replaced
    with `all_decided=len(held) > 0 and outstanding == 0` and this guard
    rerun. Observed:
        E       AssertionError: an empty group set must leave the gate open
        E       assert False
        E        +  where False = ResolveGate(outstanding=0, decided=0, all_decided=False).all_decided
    """
    gate = conflict_model.resolve_gate(conflict_model.ConflictDecisions(), [])
    assert gate.outstanding == 0
    assert gate.decided == 0
    assert gate.all_decided, "an empty group set must leave the gate open"


def test_a_bulk_resolution_settles_only_the_groups_that_collection_holds():
    """A bulk action for the source at input index 2 settles the group
    that source holds a record in and leaves the other one counted by the
    gate, rather than taking someone else's answer for it (DL-154).

    Index 2 is the second source added, which the run-wide keep-first
    picker would not choose, so this cannot pass by coinciding with that
    picker's own answer.

    Mutation: resolve_all's `if reference is not None:` in
    traktor_nml/gui/conflict_model.py was replaced with
    `if reference is None: reference = candidate_reference(group.candidates[0])`
    followed by the unconditional resolve, and this guard rerun.
    Observed:
        E       AssertionError: a group the collection holds no record in must stay undecided
        E       assert 0 == 1
        E        +  where 0 = ResolveGate(outstanding=0, decided=2, all_decided=True).outstanding
    """
    groups = _two_groups()
    decisions = conflict_model.ConflictDecisions()
    decisions.resolve_all(groups, conflict_model.reference_from_input(2))

    gate = conflict_model.resolve_gate(decisions, groups)
    assert gate.outstanding == 1, (
        "a group the collection holds no record in must stay undecided"
    )
    assert decisions.resolutions(groups) == {"track.mp3": (2, "track.mp3")}


def test_a_pick_names_a_candidate_reference_rather_than_a_collection_token():
    """The resolution a pick records is the (input index, primary key)
    pair naming the record that wins, not a base-or-source word: one file
    held by two collections carries the identical location-derived key,
    so the pair is the only thing that tells the two records apart
    (DL-004, DL-148).

    Mutation: resolve()'s recorded value was replaced with
    `_Decision("source", group.member_keys, group.candidates)` in
    traktor_nml/gui/conflict_model.py and this guard rerun. Observed:
        E       AssertionError: a resolution names the record that wins, as an (input index, primary key [...]
        E       assert 'source' == (2, 'track.mp3')
    """
    groups = _two_groups()
    decisions = conflict_model.ConflictDecisions()
    decisions.resolve(groups[0], (2, "track.mp3"))

    held = decisions.resolutions(groups)["track.mp3"]
    assert held == (2, "track.mp3"), (
        "a resolution names the record that wins, as an "
        "(input index, primary key) pair"
    )
    assert not isinstance(held, str)


def test_two_collections_holding_one_answer_are_one_candidate():
    """A group whose two sources hold identical values offers two answers
    over three records, and deciding the shared one settles both sources
    at once - the reference recorded is the contributor of lowest input
    index (DL-148, DL-150).

    Mutation: candidate_reference's `candidate.members[0]` was replaced
    with `candidate.members[-1]` in traktor_nml/gui/conflict_model.py and
    this guard rerun. Observed:
        E       AssertionError: the shared answer records its lowest contributor
        E       assert (2, 'track.mp3') == (1, 'track.mp3')
        E
        E         At index 0 diff: 2 != 1
        E         Use -v to get more diff
    """
    group = _group("track.mp3", ("Base", (0,)), ("Agreed", (1, 2)))
    decisions = conflict_model.ConflictDecisions()
    decisions.resolve(group, (2, "track.mp3"))

    assert decisions.resolutions([group])["track.mp3"] == (1, "track.mp3"), (
        "the shared answer records its lowest contributor"
    )
    assert conflict_model.resolve_gate(decisions, [group]).all_decided


def test_a_digit_names_the_answer_at_that_position_counting_from_one():
    """Specs binds digits 1-9 to candidate picking, and the page renders
    the same digit beside each answer, so digit 1 names the first answer
    and a digit past the group's answers names none (DL-071).

    Mutation: candidate_for_digit's `candidates[digit - 1]` was replaced
    with `candidates[digit]` in traktor_nml/gui/conflict_model.py and
    this guard rerun. Observed:
        E       AssertionError: digit 1 names the first answer
        E       assert ConflictCandi...track.mp3'),)) == ConflictCandi...track.mp3'),))
        E
        E         Differing attributes:
        E         ['values', 'members']
        E
    """
    group = _group("track.mp3", ("Base", (0,)), ("Alpha", (1,)))
    first = conflict_model.candidate_for_digit(group.candidates, 1)
    assert first == group.candidates[0], "digit 1 names the first answer"
    assert conflict_model.candidate_for_digit(group.candidates, 2) == group.candidates[1]
    assert conflict_model.candidate_for_digit(group.candidates, 3) is None
    assert conflict_model.candidate_for_digit(group.candidates, 0) is None


# conflict_model's freedom from nicegui is enforced by the AST walk in
# tests/test_gui_view_boundary.py, which reads every module under
# traktor_nml/gui/ against the allowlist DL-069 names and is the one
# place that rule is held. A second reading here would either duplicate
# that walk or, read as file text, forbid this module from naming the
# framework in a comment describing its own boundary. What the guards
# above hold instead is the consequence: each runs under the system
# interpreter, which has no nicegui installed, so an import added to
# conflict_model.py stops this whole file at collection.
