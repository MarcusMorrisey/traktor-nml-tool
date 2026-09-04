"""The operator's conflict decisions and the rows they produce, with no
framework import.

Two axes are kept apart throughout this module, the way review_model.py
keeps the matcher's status apart from the operator's decision: a
ConflictGroup is what the run found - one identity group's key, its
divergent attribute names, its member primary keys and each side's
values - and ConflictDecisions is what the operator said about it, one
of undecided, base or source per identity key. A key absent from the
decision mapping reads back undecided, so a fresh set and one reset key
by key behave identically.

Re-attachment across a re-preview compares membership rather than
trusting the key alone. record_keys cascades through every tier and
group_identities unions across them, so an added source can pull a
record into a group or merge two groups into one; a pick made against
one member set says nothing about a larger one. A held decision stands
only where its identity key names a group whose member primary keys are
the identical set, and a key naming no group at all, or a group whose
member set differs, leaves the row undecided and counted toward
outstanding. A re-preview after a source is added therefore refuses the
write and shows the affected rows again rather than applying a stale
pick (DL-114, DL-115).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from ..matching import MatchConfidence
from ..model import EntryRecord
from ..splice import ConflictRow, SpliceResult, group_identities, group_identity_key

# The three decision states one identity key can carry. base and source
# are the two tokens _resolve_conflicts' resolutions mapping accepts;
# undecided is this module's own reading of a key the mapping omits, and
# is never handed to the core.
UNDECIDED = "undecided"
BASE = "base"
SOURCE = "source"

SIDES = frozenset({BASE, SOURCE})

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
CONFLICTS_OUTSTANDING = "conflicts_outstanding"

# Where a group holds more than one record on a side, that side's cell
# names every distinct value it carries rather than picking one, since
# the pick is exactly what the operator has not made yet.
_VALUE_SEPARATOR = " / "

# What a side holding no record at all reads as: a group with no base
# record is settled by the run-wide picker over its non-base members, so
# its base column has nothing to show.
ABSENT = ""


@dataclass(frozen=True)
class ConflictGroup:
    """One conflicting identity group as the run reported it.

    member_keys is the set the re-attachment rule compares: the primary
    keys of every record the group holds, across every input.
    """

    identity_key: str
    attrs: tuple[str, ...]
    member_keys: frozenset[str]
    base_values: tuple[str, ...]
    source_values: tuple[str, ...]


@dataclass(frozen=True)
class ConflictRowView:
    """One rendered row: the group plus the operator's decision on it."""

    identity_key: str
    attrs: tuple[str, ...]
    base_values: tuple[str, ...]
    source_values: tuple[str, ...]
    decision: str


@dataclass(frozen=True)
class WriteRefusal:
    """Why a write cannot proceed. outstanding is the count of undecided
    conflict rows and is set only for CONFLICTS_OUTSTANDING, since a run
    that never happened has no rows to count."""

    reason: str
    outstanding: Optional[int] = None


def _side_values(
    members: Sequence[tuple[int, EntryRecord]], attrs: tuple[str, ...]
) -> tuple[str, ...]:
    values = []
    for attr in attrs:
        distinct = sorted({str(getattr(record, attr)) for _, record in members})
        values.append(_VALUE_SEPARATOR.join(distinct))
    return tuple(values)


# The attrs a ConflictRow carries when it reports something other than a
# metadata divergence: splice.py builds these two from a literal rather
# than from a list of divergent attribute names, and neither names an
# identity group a per-key resolution can settle.
NON_METADATA_ROW_ATTRS = frozenset({"playlist_name", "ambiguous_redirect"})


def conflict_groups(
    conflict_rows: Iterable[ConflictRow],
    records_by_input: list[list[EntryRecord]],
    confidence: MatchConfidence,
) -> list[ConflictGroup]:
    """The conflict rows a run reported, paired with the membership and
    the per-side values of the identity group each one names.

    Grouping is re-derived through splice.group_identities over the same
    records the run merged, so the identity keys here are the keys
    _resolve_conflicts settles on and the membership is the membership it
    grouped. A reported row whose key names no cross-input group - the
    duplicate-playlist-name and ambiguous-redirect rows the abort paths
    report under the same ConflictRow shape - names no per-key resolution
    and is left out.
    """
    members_by_key: dict[str, list[tuple[int, EntryRecord]]] = {}
    for members in group_identities(records_by_input, confidence).values():
        if len({idx for idx, _ in members}) == 1:
            continue
        members_by_key[group_identity_key(members)] = members

    groups: list[ConflictGroup] = []
    seen: set[str] = set()
    for row in conflict_rows:
        if row.attrs in NON_METADATA_ROW_ATTRS:
            continue
        members = members_by_key.get(row.identity_key)
        if members is None or row.identity_key in seen:
            continue
        seen.add(row.identity_key)
        attrs = tuple(row.attrs.split(","))
        base_members = [(idx, r) for idx, r in members if idx == 0]
        source_members = [(idx, r) for idx, r in members if idx != 0]
        groups.append(
            ConflictGroup(
                identity_key=row.identity_key,
                attrs=attrs,
                member_keys=frozenset(record.primary_key for _, record in members),
                base_values=(
                    _side_values(base_members, attrs)
                    if base_members
                    else (ABSENT,) * len(attrs)
                ),
                source_values=_side_values(source_members, attrs),
            )
        )
    return groups


@dataclass(frozen=True)
class _Decision:
    """One identity key's pick together with the member primary keys it
    was made against - the set re-attachment compares."""

    side: str
    member_keys: frozenset[str]


class ConflictDecisions:
    """The operator's per-key picks.

    Every key starts absent from _decisions, which decision() reads back
    as undecided - the same state a key reset by reset() reaches, so a
    fresh set and one reset key by key behave identically.
    """

    def __init__(self) -> None:
        self._decisions: dict[str, _Decision] = {}

    def resolve(self, group: ConflictGroup, side: str) -> None:
        """Set one group to base or source, recording the member set the
        pick is made against. Any other token is a programming error in
        the caller, not an operator-reachable state."""
        if side not in SIDES:
            raise ValueError(f"side must be one of {sorted(SIDES)}, got {side!r}")
        self._decisions[group.identity_key] = _Decision(side, group.member_keys)

    def reset(self, identity_key: str) -> None:
        """Return one key to undecided, whether or not it is decided."""
        self._decisions.pop(identity_key, None)

    def decision(self, group: ConflictGroup) -> str:
        """The pick held for this group, or undecided.

        A held pick stands only where the group's member primary keys are
        the identical set it was made against; a changed set reads back
        undecided (DL-115).
        """
        held = self._decisions.get(group.identity_key)
        if held is None or held.member_keys != group.member_keys:
            return UNDECIDED
        return held.side

    def resolve_all(self, groups: Iterable[ConflictGroup], side: str) -> None:
        """Set every undecided group to one side, leaving a group already
        decided the other way standing."""
        for group in groups:
            if self.decision(group) == UNDECIDED:
                self.resolve(group, side)

    def outstanding(self, groups: Iterable[ConflictGroup]) -> int:
        """How many of these groups read undecided - which counts a group
        whose membership no longer matches its held pick."""
        return sum(1 for group in groups if self.decision(group) == UNDECIDED)

    def resolutions(self, groups: Iterable[ConflictGroup]) -> dict[str, str]:
        """The mapping _resolve_conflicts takes: only decided keys, only
        keys these groups name. An undecided key is omitted rather than
        carrying a token, so on_conflict settles it or the run aborts, and
        a decision for a key no group names contributes nothing."""
        mapping: dict[str, str] = {}
        for group in groups:
            side = self.decision(group)
            if side != UNDECIDED:
                mapping[group.identity_key] = side
        return mapping

    def rows(self, groups: Iterable[ConflictGroup]) -> list[ConflictRowView]:
        """What the page renders, one row per group, in the order the run
        reported them."""
        return [
            ConflictRowView(
                identity_key=group.identity_key,
                attrs=group.attrs,
                base_values=group.base_values,
                source_values=group.source_values,
                decision=self.decision(group),
            )
            for group in groups
        ]


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
    nothing; a held result that aborted answers CONFLICTS_OUTSTANDING
    with the count of rows still undecided (DL-111).
    """
    if result is None:
        return WriteRefusal(NO_PREVIEW)
    if result.output is not None:
        return None
    return WriteRefusal(CONFLICTS_OUTSTANDING, decisions.outstanding(groups))


def write_refusal_sentence(refusal: WriteRefusal) -> str:
    """The operator-facing sentence for one refusal, naming what is wrong
    and which control fixes it. Falls back to naming the raw reason
    rather than raising, so an unmapped reason degrades to a bare but
    visible label instead of breaking the render."""
    if refusal.reason == NO_PREVIEW:
        return "No preview has been run. Run Preview to see what this merge would write."
    if refusal.reason == CONFLICTS_OUTSTANDING:
        return (
            f"The preview refused: {refusal.outstanding} conflict(s) still to decide. "
            "Choose base or source for each row above, then run Preview again."
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
    if reason == IS_A_SOURCE:
        return (
            "That collection is already a source. Remove it from the list "
            "first, or choose a different file to repair."
        )
    return f"Refused: {reason}"
