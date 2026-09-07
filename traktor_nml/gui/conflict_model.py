"""The operator's conflict decisions and the rows they produce, with no
framework import.

Two axes are kept apart throughout this module, the way review_model.py
keeps the matcher's status apart from the operator's decision: a
ConflictGroup is what the run found - one identity group's key, its
divergent attribute names, its member primary keys and the distinct
answers its records offer - and ConflictDecisions is what the operator
said about it, either undecided or a candidate reference naming one of
those answers. A key absent from the decision mapping reads back
undecided, so a fresh set and one reset key by key behave identically.

A candidate reference is an (input index, primary key) pair, which is
what _resolve_conflicts reads and what tells apart two records for one
file in two inputs, whose primary keys are identical because the key is
derived from the location (DL-004, DL-148). base and source survive here
as operator-facing words on the page's labels and in the refusal
sentence; they are no decision value this module carries.

Re-attachment across a re-preview compares the answers on offer rather
than trusting the key alone. record_keys cascades through every tier and
group_identities unions across them, so an added source can pull a
record into a group, merge two groups into one, or add an answer to a
group whose member primary keys do not change at all - a source holding
one file at a location an existing member already holds contributes the
primary key the group already carries, so the frozenset is the same set.
A held pick therefore stands only where its identity key names a group
whose member primary keys are the identical set AND whose candidates are
the identical tuple; a key naming no group, a group whose membership
differs, or a group whose answers differ leaves the row undecided and
counted toward outstanding. A re-preview after a source is added refuses
the write and shows the affected rows again rather than applying a pick
made against answers that are no longer the answers on offer (DL-114,
DL-115, DL-158).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from ..splice import ConflictCandidate, ConflictRow, SpliceResult

# The one decision state this module owns as a token. A decided key
# carries an (input index, primary key) pair instead; undecided is this
# module's own reading of a key the decision mapping omits, and is never
# handed to the core.
UNDECIDED = "undecided"

# A reference to one answer a group offers: the (input index, primary
# key) pair _resolve_conflicts reads to name the record that wins.
CandidateRef = tuple[int, str]

# The reasons a write cannot proceed, as write_refusal returns them.
NO_PREVIEW = "no_preview"
# The reasons a collection the operator picked is refused a place on the
# page. A collection named twice contributes nothing the first naming does
# not, and one naming both sides would have the page repair a collection
# from itself, so each is refused at the control rather than folded into a
# run whose result would not say why it looked wrong.
ALREADY_LISTED = "already_listed"
IS_THE_BASE = "is_the_base"
IS_A_SOURCE = "is_a_source"
# The output path naming a collection the run reads. Refused for the same
# reason as the two above and stated at the same place: an output written
# over an input would destroy the collection the repair was read from.
OUTPUT_IS_AN_INPUT = "output_is_an_input"
CONFLICTS_OUTSTANDING = "conflicts_outstanding"
RUN_REFUSED = "run_refused"

# The error token assemble_output reports when it aborts on conflicts the
# resolutions did not settle. It is this module's own token: the page
# reads it from here rather than declaring a second copy, so the token the
# refusal is keyed on and the token the page renders rows for are one
# string (DL-111).
CONFLICT_ABORT_TOKEN = "unresolved_conflicts"


@dataclass(frozen=True)
class ConflictGroup:
    """One conflicting identity group as the run reported it.

    member_keys and candidates are the two sets re-attachment compares:
    the primary keys of every record the group holds across every input,
    and one candidate per distinct answer over attrs, each naming the
    records that supply it. Neither alone sees every change a re-preview
    can make to a group (DL-158).
    """

    identity_key: str
    attrs: tuple[str, ...]
    member_keys: frozenset[str]
    candidates: tuple[ConflictCandidate, ...]


@dataclass(frozen=True)
class ConflictRowView:
    """One rendered row: the group's answers plus the operator's decision
    over them. decision is UNDECIDED or the candidate reference picked."""

    identity_key: str
    attrs: tuple[str, ...]
    candidates: tuple[ConflictCandidate, ...]
    decision: object


@dataclass(frozen=True)
class WriteRefusal:
    """Why a write cannot proceed. outstanding is the count of undecided
    conflict rows and is set only for CONFLICTS_OUTSTANDING, since a run
    that never happened has no rows to count. errors carries the held
    run's own error strings and is set only for RUN_REFUSED, since that
    is the reason whose sentence has to name what the run said; it is
    empty for every other reason.
    """

    reason: str
    outstanding: Optional[int] = None
    errors: tuple[str, ...] = ()


def candidate_reference(candidate: ConflictCandidate) -> CandidateRef:
    """The pair a pick on this candidate records: its contributor of
    lowest input index. The contributors agree on every divergent
    attribute by construction, so the values written are the same
    whichever one is named, and naming the lowest makes the recorded pair
    deterministic (DL-150)."""
    return candidate.members[0]


def candidate_holding_input(
    candidates: Iterable[ConflictCandidate], input_index: int
) -> Optional[ConflictCandidate]:
    """The answer the collection at this input index supplies, or None
    where it holds no record in the group at all. A bulk action reads
    this to settle the groups its collection has an answer for and to
    leave the rest alone (DL-154)."""
    for candidate in candidates:
        if any(idx == input_index for idx, _ in candidate.members):
            return candidate
    return None


def reference_from_input(
    input_index: int,
) -> Callable[[tuple[ConflictCandidate, ...]], Optional[CandidateRef]]:
    """The predicate a bulk action for one collection hands resolve_all:
    it answers the reference of the candidate that collection supplies,
    or None for a group the collection holds no record in."""

    def predicate(candidates: tuple[ConflictCandidate, ...]) -> Optional[CandidateRef]:
        candidate = candidate_holding_input(candidates, input_index)
        return None if candidate is None else candidate_reference(candidate)

    return predicate


# The attrs a ConflictRow carries when it reports something other than a
# metadata divergence: splice.py builds these two from a literal rather
# than from a list of divergent attribute names, and neither names an
# identity group a per-key resolution can settle.
NON_METADATA_ROW_ATTRS = frozenset({"playlist_name", "ambiguous_redirect"})


def conflict_groups(conflict_rows: Iterable[ConflictRow]) -> list[ConflictGroup]:
    """The conflicting identity groups a run reported, projected from the
    rows the run itself produced.

    Each row carries the membership and the candidates the run's own
    grouping derived, so this is a projection and no grouping happens
    here: the identity keys, the member sets and the answers are exactly
    the ones _resolve_conflicts settled on, and cannot drift from them.
    No record and no MatchConfidence enters this call.

    A row that names no identity group a per-key resolution can settle is
    left out: the duplicate-playlist-name and ambiguous-redirect rows the
    abort paths report under the same ConflictRow shape are recognised by
    their attrs, and any row carrying no member keys names no group
    either. Where several rows name one key, the first stands.
    """
    groups: list[ConflictGroup] = []
    seen: set[str] = set()
    for row in conflict_rows:
        if row.attrs in NON_METADATA_ROW_ATTRS:
            continue
        if not row.member_keys or row.identity_key in seen:
            continue
        seen.add(row.identity_key)
        groups.append(
            ConflictGroup(
                identity_key=row.identity_key,
                attrs=tuple(row.attrs.split(",")),
                member_keys=row.member_keys,
                candidates=row.candidates,
            )
        )
    return groups


@dataclass(frozen=True)
class _Decision:
    """One identity key's pick together with what it was made against -
    the member primary keys and the answers on offer, which are the two
    things re-attachment compares."""

    reference: CandidateRef
    member_keys: frozenset[str]
    candidates: tuple[ConflictCandidate, ...]


class ConflictDecisions:
    """The operator's per-key picks.

    Every key starts absent from _decisions, which decision() reads back
    as undecided - the same state a key reset by reset() reaches, so a
    fresh set and one reset key by key behave identically.
    """

    def __init__(self) -> None:
        self._decisions: dict[str, _Decision] = {}

    def resolve(self, group: ConflictGroup, reference: CandidateRef) -> None:
        """Pick one of this group's answers, recording the member set and
        the candidate set the pick is made against.

        The reference names any contributor of one candidate, and the
        pick recorded is that candidate's own reference, so two
        collections supplying one answer record the same pair (DL-150). A
        reference no candidate of the group carries is a programming
        error in the caller rather than stale operator input: this module
        builds the mapping from the groups it holds, so it never emits a
        pair its group does not carry (DL-159).
        """
        for candidate in group.candidates:
            if tuple(reference) in candidate.members:
                self._decisions[group.identity_key] = _Decision(
                    candidate_reference(candidate), group.member_keys, group.candidates
                )
                return
        raise ValueError(
            f"reference {reference!r} names no candidate of group {group.identity_key!r}"
        )

    def reset(self, identity_key: str) -> None:
        """Return one key to undecided, whether or not it is decided."""
        self._decisions.pop(identity_key, None)

    def decision(self, group: ConflictGroup) -> object:
        """The pick held for this group as a candidate reference, or
        UNDECIDED.

        A held pick stands only where the group's member primary keys are
        the identical set and its candidates are the identical tuple it
        was made against; either one differing reads back undecided,
        since a source added at a location an existing member already
        holds leaves the member set untouched while changing the answers
        on offer (DL-115, DL-158).
        """
        held = self._decisions.get(group.identity_key)
        if held is None:
            return UNDECIDED
        if held.member_keys != group.member_keys or held.candidates != group.candidates:
            return UNDECIDED
        return held.reference

    def resolve_all(
        self,
        groups: Iterable[ConflictGroup],
        predicate: Callable[[tuple[ConflictCandidate, ...]], Optional[CandidateRef]],
    ) -> None:
        """Settle every undecided group the predicate answers a reference
        for, leaving a group already decided standing and leaving a group
        the predicate answers None for undecided.

        A bulk action for one collection hands the predicate built by
        reference_from_input, so a group that collection holds no record
        in keeps no value of anyone else's and stays counted by
        outstanding (DL-154).
        """
        for group in groups:
            if self.decision(group) != UNDECIDED:
                continue
            reference = predicate(group.candidates)
            if reference is not None:
                self.resolve(group, reference)

    def outstanding(self, groups: Iterable[ConflictGroup]) -> int:
        """How many of these groups read undecided - which counts a group
        whose membership or whose answers no longer match its held
        pick."""
        return sum(1 for group in groups if self.decision(group) == UNDECIDED)

    def resolutions(self, groups: Iterable[ConflictGroup]) -> dict[str, CandidateRef]:
        """The mapping _resolve_conflicts takes: an (input index, primary
        key) pair per decided key, only for keys these groups name. An
        undecided key is omitted entirely rather than carrying a token, so
        on_conflict settles it or the run aborts, and a decision for a key
        no group names contributes nothing."""
        mapping: dict[str, CandidateRef] = {}
        for group in groups:
            decision = self.decision(group)
            if decision != UNDECIDED:
                mapping[group.identity_key] = decision  # type: ignore[assignment]
        return mapping

    def rows(self, groups: Iterable[ConflictGroup]) -> list[ConflictRowView]:
        """What the page renders, one row per group, in the order the run
        reported them."""
        return [
            ConflictRowView(
                identity_key=group.identity_key,
                attrs=group.attrs,
                candidates=group.candidates,
                decision=self.decision(group),
            )
            for group in groups
        ]


@dataclass(frozen=True)
class ResolveGate:
    """The resolve step's own gate: how many groups carry no answer,
    how many carry one, and whether the step may be left.

    One value carrying both, because the footer's sentence and the
    advancing control's enabled state are one fact read twice: a count
    computed for the sentence and an emptiness computed again for the
    control can disagree, and the disagreement shows as a control the
    operator can press over a sentence saying they cannot (DL-204).
    """

    # Groups carrying no answer yet: the number the footer's sentence
    # prints.
    outstanding: int
    # Groups carrying one: the second number of the same sentence, held
    # beside the first so the two are read off one walk rather than
    # counted twice.
    decided: int
    # Whether the resolve step may be left, which is `outstanding == 0`
    # and not a second count over the groups (DL-204).
    all_decided: bool

    @property
    def note(self) -> str:
        """The footer's sentence for this gate.

        Held on the gate rather than formatted at the call site for the
        same reason all_decided is: the sentence and the advancing
        control's enabled state are one fact, and a sentence written
        unconditionally beside a control that opens says writing is shut
        while the operator is looking at the control that opens it,
        which is the disagreement this class exists to prevent
        (DL-204).
        """
        if self.all_decided:
            return "Every track has an answer. Writing is open."
        return (
            f"{self.outstanding} still to decide. Writing stays closed "
            "until every one has an answer."
        )


def resolve_gate(
    decisions: ConflictDecisions, groups: Iterable[ConflictGroup]
) -> ResolveGate:
    """The gate over these groups: the count of undecided groups and
    whether every one carries an answer.

    groups is walked once and all_decided is derived from that one
    count, so the two can never disagree. A group whose membership or
    whose answers differ from the ones its held pick was made against
    reads undecided here for the reason decision() gives, so a
    re-preview offering different answers shuts the gate (DL-158,
    DL-204).

    No group at all reads zero outstanding and an open gate: a run that
    reported no divergence has nothing to resolve, and the step it gates
    is one the operator passes straight through.
    """
    held = list(groups)
    outstanding = decisions.outstanding(held)
    return ResolveGate(
        outstanding=outstanding,
        decided=len(held) - outstanding,
        all_decided=outstanding == 0,
    )


def candidate_for_digit(
    candidates: tuple[ConflictCandidate, ...], digit: int
) -> Optional[ConflictCandidate]:
    """The answer Specs' digit keys name, counting from one, or None
    where the group offers no such answer.

    Specs binds digits 1-9 to candidate picking and the page renders the
    same digit beside each answer, so the digit and the position are one
    fact and it is counted here rather than at a call site: a page
    subtracting one itself would hold a decision rule the suite cannot
    reach (DL-069, DL-071). A digit outside the group's answers reads
    None rather than raising, which is the same answer keymap.dispatch
    gives for a digit past the focused row's candidate count.
    """
    if digit < 1 or digit > len(candidates):
        return None
    return candidates[digit - 1]


def write_refusal(
    result: Optional[SpliceResult],
    decisions: ConflictDecisions,
    groups: Iterable[ConflictGroup],
) -> Optional[WriteRefusal]:
    """Why the write cannot proceed, or None when it can.

    SpliceResult's documented invariant is that output is None exactly
    when errors is non-empty, so output alone cannot tell a run that
    aborted from a run that never happened. The absent result is read
    first and answers NO_PREVIEW; a held result carrying output refuses
    nothing.

    A held result that aborted is read by its errors rather than by
    output alone, because assemble_output aborts on many things besides
    conflicts - an ambiguous playlist name, an ambiguous redirect, a
    missing collection, a location collision, an unresolved reference.
    Only errors carrying CONFLICT_ABORT_TOKEN answer
    CONFLICTS_OUTSTANDING with the count of rows still undecided; every
    other abort answers RUN_REFUSED carrying the run's own error strings,
    so the sentence names what the run said instead of a conflict count
    the run never reported (DL-111).
    """
    if result is None:
        return WriteRefusal(NO_PREVIEW)
    if result.output is not None:
        return None
    errors = tuple(result.errors)
    if CONFLICT_ABORT_TOKEN in errors:
        return WriteRefusal(CONFLICTS_OUTSTANDING, decisions.outstanding(groups))
    return WriteRefusal(RUN_REFUSED, errors=errors)


def run_assembled(result) -> bool:
    """Whether a held run produced an output to report.

    A run that refused is a held result carrying no output, and the two
    are told apart here rather than at a call site: the page reads this
    instead of testing `result.output is None` itself, which is the test
    DL-111 keeps out of the view because it reads a run that aborted and
    a run that never happened as the same thing.
    """
    return result is not None and result.output is not None


def run_is_current(used, decisions: "ConflictDecisions", groups) -> bool:
    """Whether a held run was assembled with the answers now given.

    `used` is the resolutions mapping the run was handed. A run assembled
    before an answer was given, or before one was changed, reports what
    some earlier set of answers produced, and the write step reports that
    run: the operator would be shown - and would write - a file assembled
    from answers they have since replaced. Comparing the mapping rather
    than a flag means a decision made and undone back to where it started
    leaves the run current (DL-225).
    """
    return used == decisions.resolutions(groups)


def write_refusal_sentence(refusal: WriteRefusal) -> str:
    """The operator-facing sentence for one refusal, naming what is wrong
    and which control fixes it. The conflict sentence names choosing a
    collection for each row, which is what the row's controls offer - one
    control per answer, each naming the collections that supply it
    (DL-160). Falls back to naming the raw reason rather than raising, so
    an unmapped reason degrades to a bare but visible label instead of
    breaking the render."""
    if refusal.reason == NO_PREVIEW:
        return "No preview has been run. Run Preview to see what this merge would write."
    if refusal.reason == CONFLICTS_OUTSTANDING:
        return (
            f"The preview refused: {refusal.outstanding} conflict(s) still to decide. "
            "Choose a collection for each row above, then run Preview again."
        )
    if refusal.reason == RUN_REFUSED:
        # The page has already drawn "Nothing was written." above the
        # controls with one line per error token, so the sentence names
        # the first of those tokens and sends the operator to that
        # report for the rest rather than inventing a count.
        named = refusal.errors[0] if refusal.errors else "the run reported no reason"
        return (
            f"The preview stopped: {named}. Nothing was written; see the "
            "report above the controls for what stopped this run."
        )
    return f"Write refused: {refusal.reason}"


def _same_file(one, other) -> bool:
    """Whether two paths name one file, compared resolved so a relative
    path, a different case on a case-insensitive volume and a path
    through a link are one collection rather than two."""
    return Path(one).resolve() == Path(other).resolve()


def source_refusal(candidate, base_path, sources) -> Optional[str]:
    """Why a collection cannot join the source list, or None.

    A candidate already on the list answers ALREADY_LISTED; one that is
    the collection being repaired answers IS_THE_BASE.
    """
    if base_path is not None and _same_file(candidate, base_path):
        return IS_THE_BASE
    if any(_same_file(candidate, listed) for listed in sources):
        return ALREADY_LISTED
    return None


def base_refusal(candidate, sources) -> Optional[str]:
    """Why a collection cannot be the one repaired, or None.

    The same collision source_refusal names, read from the other side:
    a candidate already taken as a source answers IS_A_SOURCE.
    """
    if any(_same_file(candidate, listed) for listed in sources):
        return IS_A_SOURCE
    return None


def output_refusal(output, base_path, sources) -> Optional[str]:
    """Why the output path cannot be written, or None.

    An output naming the collection being repaired or any source answers
    OUTPUT_IS_AN_INPUT. An empty path answers None: a path not yet chosen
    is not a path that collides, and the control that asks for one says
    so in its own words.

    One rule, read by the set-up step's own line about the output and by
    the write's refusal, so the page cannot describe a path as safe and
    then refuse to write it (DL-222).
    """
    if not output:
        return None
    against = [path for path in (base_path, *sources) if path]
    if any(_same_file(output, path) for path in against):
        return OUTPUT_IS_AN_INPUT
    return None


def selection_refusal_sentence(reason: str) -> str:
    """The operator-facing sentence for one selection refusal, naming
    what is wrong and which control fixes it. Falls back to naming the
    raw reason rather than raising."""
    if reason == ALREADY_LISTED:
        return "That collection is already on the list. Remove it first to add it again."
    if reason == IS_THE_BASE:
        return (
            "That is the collection being repaired. A collection cannot take "
            "playlists from itself; choose a different file."
        )
    if reason == OUTPUT_IS_AN_INPUT:
        return (
            "The output path names a collection this run reads. Choose a "
            "different name, so nothing you gave it is overwritten."
        )
    if reason == IS_A_SOURCE:
        return (
            "That collection is already a source. Remove it from the list "
            "first, or choose a different file to repair."
        )
    return f"Refused: {reason}"
