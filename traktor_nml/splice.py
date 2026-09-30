"""Merge a base NML with further NML files while every playlist stays valid.

Scope note: the base input is authoritative for its own COLLECTION and
playlists - its entries keep their positions and their identities, and the
merged collection holds at most one entry per LOCATION (DL-004). The only
bytes of a base ENTRY a run rewrites are the attribute values the record an
operator's resolution names carries, substituted inside base's own entry span; the base
input file on disk is never written (DL-123).

Track identity across inputs uses the shared record_keys tier ordering,
cascaded through every tier via union-find (not just each record's own
top-tier key) so two copies of one track that happen to agree on a lower tier
but not the top one still land in the same identity group, since splice needs
N-way grouping rather than pairwise old-vs-new comparison. When a base record and a
non-base record share an identity, the base record always wins and keeps its
entry; a resolution names which record supplies that entry's tracked
attribute values, and --on-conflict's keep-first/keep-last only disambiguates
among duplicates that are *not* shared with base. A metadata conflict (any
differing attribute between two copies of one identity) is settled either
by a per-key resolutions mapping naming that one identity group or by the
run-wide --on-conflict policy; a divergence neither of them settles aborts
the whole write, and the conflict report is written either way (DL-008,
DL-104). Fragments no rename or redirect touched are transplanted
as source byte spans (spans.py); only renamed playlists and redirected
PRIMARYKEY values are re-serialised.
"""

from __future__ import annotations

import html
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from . import metadata_tier
from .confidence import MatchConfidence
from .matching import record_keys
from .model import EntryRecord, collection_entries, collection_records
from .playlists import (
    drop_unresolvable_entries,
    find_playlist_nodes,
    import_playlists,
    merged_playlist_entries,
    node_primary_keys,
    playlist_path_pairs,
    redirected_playlist_keys,
)
from .spans import OutputBuilder, SpanIndex, find_element_span
from .textpatch import patch_entry_attributes
from .xmlio import ET, parse_xml_bytes

# Imported rather than held here: metadata_tier is the one definition of
# the six names and of which of them carry an operator judgement, and a
# second tuple beside it would drift from the partition the tier is
# decided on (DL-326). The name keeps its underscore so answer_detail's
# import of it, and every test reading it, stand unchanged.
_TRACKED_ATTRS = metadata_tier.TRACKED_ATTRS

# The assembled output is scanned for these rather than parsed: the audit
# below reads the text the run is about to return, and a second lxml parse
# of the largest file in the run is the cost it exists to avoid. Both
# patterns read attributes this module writes itself, in the order it
# writes them.
_EMITTED_KEY_RE = re.compile(r'<PRIMARYKEY\b[^>]*\bKEY="([^"]*)"')
_EMITTED_LOCATION_RE = re.compile(
    r'<LOCATION\b[^>]*\bDIR="([^"]*)"[^>]*\bFILE="([^"]*)"[^>]*\bVOLUME="([^"]*)"'
)


@dataclass(frozen=True)
class ConflictCandidate:
    """One distinct answer a metadata-diverging group offers.

    values holds one value per name in the row's attrs, in that order.
    members names every record supplying exactly those values, as
    (input index, primary key) pairs sorted by input index: the primary
    key is derived from the location (DL-004), so two records for one
    file in two inputs carry the identical key and the input index is
    what tells them apart (DL-148).
    """

    values: tuple[str, ...]
    members: tuple[tuple[int, str], ...]


@dataclass
class ConflictRow:
    """One row a run reports about a group it could not merge silently.

    identity_key, attrs and resolution are the three columns the CSV
    conflict report writes. member_keys and candidates are what the
    interactive page needs to show and re-attach the row without grouping
    the collections a second time: member_keys is the primary key of every
    record the group holds across every input, and candidates holds one
    entry per distinct tuple of divergent-attribute values, each naming
    the records that supply it, so two inputs agreeing on every divergent
    attribute present as one answer rather than two (DL-149, DL-150). A
    row reporting something other than a metadata divergence names no
    identity group, and keeps the empty defaults.

    agreed holds every tracked attribute OUTSIDE the divergent set, in
    _TRACKED_ATTRS order, each paired with the single value every member
    of the group holds for it. attrs names what the group could not
    agree on and agreed names what it did, so the two together are the
    whole record the group describes and a screen reading them shows a
    record rather than a diff. It defaults empty, so a row reporting
    something other than a metadata divergence keeps the shape it has.
    """

    identity_key: str
    attrs: str
    resolution: str
    member_keys: frozenset[str] = frozenset()
    candidates: tuple[ConflictCandidate, ...] = ()
    # agreed rides beside attrs rather than widening it: attrs is the
    # third column of the conflict CSV and of the line splice_cmd
    # prints, so a field holding the agreeing names keeps that recorded
    # output exactly where it stands (ref: DL-244).
    agreed: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SettledRow:
    """One group the tier answered without asking the operator.

    identity_key names the group the way group_identity_key does, so a
    settled row and a conflict row name a group by the one rule.
    attrs holds the measured attribute names the group diverged on, in
    metadata_tier.TRACKED_ATTRS order; values_by_attr holds the values
    each of those attributes took across the members, so a reader can
    say what the two numbers were without a second look at the records.
    winner is the (input index, primary key) pair naming the record whose
    values the output carries - the shape _candidates already names a
    contributor by and conflict_model calls a CandidateRef. The pair
    rather than the key alone because base and a source describing the
    one LOCATION carry the identical primary key, the commonest settled
    shape there is, so a key standing alone equals identity_key and says
    which record won of neither. DL-148 asks a settled group to name the
    record, never a base-or-source token, and the index is the half that
    names it.
    outliers holds the readings metadata_tier.outlier_attrs answers for
    this group - empty for the ordinary 2 KB drift.

    A row, not a sentence. splice reports what the run found and a
    reader divides and words it, which is why no count and no plural
    stands here (DL-215, DL-331).
    """

    identity_key: str
    attrs: tuple[str, ...]
    values_by_attr: tuple[tuple[str, tuple[str, ...]], ...]
    winner: tuple[int, str]
    outliers: tuple[metadata_tier.OutlierReading, ...] = ()

    @property
    def is_outlier(self) -> bool:
        """Whether any of this group's measured attributes reads past the
        band, which is what a caller divides the run's settled rows on to
        get its listing. Read off the readings the row already carries,
        so a count of outlying groups and the rows drawn for them are the
        one set (DL-330, DL-331)."""
        return bool(self.outliers)


@dataclass
class SpliceResult:
    """output is None exactly when errors is non-empty - an abort with
    nothing written (extending DL-012's validate-before-write invariant
    to a multi-input merge); conflict_rows is populated on every run
    regardless of outcome, even a clean one (DL-008).

    conflict_rows are the groups the run puts to the operator;
    settled_rows are the groups the tier answered for them. The two
    lists are disjoint, and stats carries a count read off each of them,
    so a surface naming how many decisions remain and how many were made
    for the operator reads both numbers off this one record (DL-215,
    DL-329, DL-331)."""
    output: Optional[str]
    stats: dict[str, object]
    conflict_rows: list[ConflictRow] = field(default_factory=list)
    # Populated on every run regardless of outcome, a clean one and an
    # abort included, for the reason DL-008 populates conflict_rows that
    # way: the groups the rule answered are part of what the run did,
    # and a reader asking what was decided for the operator must not
    # have to infer it from a count that is missing (DL-329).
    settled_rows: list[SettledRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def group_identities(
    records_by_input: list[list[EntryRecord]], confidence: MatchConfidence
) -> dict[int, list[tuple[int, EntryRecord]]]:
    """Group collection records from every input into identity groups using
    the full record_keys tier cascade: two records are grouped together if
    they share ANY eligible tier's key, not only their own single
    highest-confidence key - e.g. one copy carrying AUDIO_ID and another copy
    of the same track missing it must still land in one group, matched
    through whichever lower tier they do share. Grouping is a union-find over
    every (tier_name, key_value) bucket across every input; a record with no
    eligible key at all never joins a bucket and so keeps its own singleton
    group."""
    all_records: list[tuple[int, EntryRecord]] = [
        (input_idx, record)
        for input_idx, records in enumerate(records_by_input)
        for record in records
    ]

    parent = list(range(len(all_records)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[max(root_a, root_b)] = min(root_a, root_b)

    buckets: dict[tuple[str, tuple], int] = {}
    for i, (_, record) in enumerate(all_records):
        for tier_name, value in record_keys(record, confidence):
            bucket_key = (tier_name, value)
            if bucket_key in buckets:
                union(i, buckets[bucket_key])
            else:
                buckets[bucket_key] = i

    groups: dict[int, list[tuple[int, EntryRecord]]] = {}
    for i, entry in enumerate(all_records):
        groups.setdefault(find(i), []).append(entry)
    return groups


def group_identity_key(members: list[tuple[int, EntryRecord]]) -> str:
    """The name a conflicting identity group answers to.

    The union-find root is an index into the flat all_records list, so it
    moves when an input is added or removed and cannot name the same set of
    records across two runs. The key is derived from the group's contents
    instead: the primary key of its sole base-input record where it holds
    one, and the sorted tuple of its member primary keys where it holds
    none. Every conflicting group spans more than one input and so holds at
    least two records, which makes the derivation total (DL-114).
    """
    base_keys = [record.primary_key for idx, record in members if idx == 0]
    if len(base_keys) == 1:
        return base_keys[0]
    return "|".join(sorted(record.primary_key for _, record in members))


class ResolvedConflicts(tuple):
    """_resolve_conflicts' result: the five values (old_to_new_key,
    conflict_rows, unresolved, new_entries, ambiguous_keys) a caller unpacks
    positionally, carrying entry_patches and settled_rows as named
    attributes.

    entry_patches is reached by name rather than as a sixth positional
    element, so every caller that unpacks the five reads the five it reads
    (DL-100's precedent, DL-104)."""

    def __new__(
        cls,
        old_to_new_key: dict[str, str],
        conflict_rows: list[ConflictRow],
        unresolved: bool,
        new_entries: list[tuple[int, EntryRecord]],
        ambiguous_keys: set[str],
        entry_patches: list[tuple[EntryRecord, dict[str, str]]],
        settled_rows: list["SettledRow"],
    ) -> "ResolvedConflicts":
        self = super().__new__(
            cls, (old_to_new_key, conflict_rows, unresolved, new_entries, ambiguous_keys)
        )
        self.entry_patches = entry_patches
        # Named beside entry_patches rather than a sixth positional
        # element, for the reason entry_patches is: every caller that
        # unpacks the five reads the five it reads (DL-100's precedent,
        # DL-104).
        self.settled_rows = settled_rows
        return self


def _candidates(
    members: list[tuple[int, EntryRecord]], attrs: list[str]
) -> tuple[ConflictCandidate, ...]:
    """The distinct answers a group offers over attrs: one candidate per
    distinct tuple of values, in the order the group first supplies them,
    each naming its contributing (input index, primary key) pairs sorted
    by input index. Records agreeing on every name in attrs collapse into
    one candidate carrying both contributors (DL-150)."""
    grouped: dict[tuple[str, ...], list[tuple[int, str]]] = {}
    for input_idx, record in members:
        values = tuple(str(getattr(record, attr)) for attr in attrs)
        grouped.setdefault(values, []).append((input_idx, record.primary_key))
    return tuple(
        ConflictCandidate(values, tuple(sorted(contributors)))
        for values, contributors in grouped.items()
    )


def _agreed(
    members: list[tuple[int, EntryRecord]], attrs: list[str]
) -> tuple[tuple[str, str], ...]:
    """The tracked attributes the group agrees on, as (name, value)
    pairs in _TRACKED_ATTRS order.

    Read off the members already grouped, in the same pass _candidates
    reads them: an attribute absent from attrs holds one value across
    every member by the way attrs was computed, so the first member's
    value is that value and no set is built a second time.

    Well defined because divergent_attrs names the attributes whose
    value set across the group's members holds more than one member: an
    attribute outside that set holds one value across every member,
    candidates included, so the value belongs to the group rather than
    to any one answer (ref: DL-245).
    """
    divergent = set(attrs)
    first = members[0][1]
    return tuple(
        (attr, str(getattr(first, attr)))
        for attr in _TRACKED_ATTRS
        if attr not in divergent
    )


def _metadata_conflict_row(
    identity_key: str,
    divergent_attrs: list[str],
    members: list[tuple[int, EntryRecord]],
    resolution: Optional[str],
) -> ConflictRow:
    """The row one metadata-diverging group reports, carrying the group's
    membership and its candidates off the members already grouped, in one
    pass and with no second look at the records."""
    return ConflictRow(
        identity_key,
        ",".join(divergent_attrs),
        resolution,
        member_keys=frozenset(record.primary_key for _, record in members),
        candidates=_candidates(members, divergent_attrs),
        agreed=_agreed(members, divergent_attrs),
    )


def _settled_row(
    identity_key: str,
    measured_attrs: tuple[str, ...],
    members: list[tuple[int, EntryRecord]],
    winner_idx: int,
    winner: EntryRecord,
) -> SettledRow:
    """The row one tier-settled group reports, read off the members
    already grouped in the same pass _candidates and _agreed read them,
    with no second walk over the records.

    winner_idx travels beside winner because the record alone cannot say
    which collection it was read from, and its primary key is the key
    every other member of the group carries: the pair is what names it
    (DL-148, DL-150)."""
    values_by_attr = tuple(
        (attr, tuple(dict.fromkeys(str(getattr(r, attr)) for _, r in members)))
        for attr in measured_attrs
    )
    return SettledRow(
        identity_key,
        tuple(measured_attrs),
        values_by_attr,
        (winner_idx, winner.primary_key),
        outliers=metadata_tier.outlier_attrs(dict(values_by_attr)),
    )


def _resolve_conflicts(
    groups: dict[int, list[tuple[int, EntryRecord]]],
    on_conflict: Optional[str],
    *,
    resolutions: Optional[dict[str, tuple[int, str]]] = None,
) -> ResolvedConflicts:
    """Return (old_to_new_key, conflict_rows, unresolved, new_entries,
    ambiguous_keys).

    resolutions maps an identity-group key to an (input index, primary key)
    pair naming one record of that group, and settles that one group;
    on_conflict settles every group the mapping does not name. A pair naming
    no member of the group settles nothing and the group falls through to
    on_conflict, or to the unresolved abort where on_conflict is None, the
    way an identity key naming no group does (DL-105, DL-153). It is a keyword parameter rather than an appended positional,
    so the positional callers read the arguments they read (DL-100's
    precedent, DL-104).

    ambiguous_keys holds every non-base primary key whose identity group
    carries more than one base record: no single base key is the right
    redirect target for it, so a reconstruction that folded it in would be
    guessing which base track the entry meant (DL-094, DL-100). The merge
    itself is unaffected - these keys still redirect to the winner for
    collection purposes - so the set is returned rather than raised, and
    only the reconstruction path treats it as fatal.

    new_entries lists (input_idx, record) for exactly the records that must
    be added to the merged COLLECTION: the sole record of a single-input
    group not owned by the base, or a cross-input group's non-base winner.
    input_idx disambiguates which source text to transplant the entry's
    span from, since two distinct records can carry identical field values.

    entry_patches, reached by name off the result, lists (base_record,
    values) for every group a resolution settles while the group holds a
    base record: base_members[0], whose ENTRY the run rewrites in place,
    paired with the group's divergent attribute values read off the record
    the pair names. Such a group's winner is base's own record and it
    contributes nothing to new_entries, so the merged COLLECTION keeps one
    entry per LOCATION (DL-004, DL-116) and the redirect target below stays
    base_members[0]. Where the group holds no base record the pair names the
    winner appended to new_entries, so there and only there a pick moves the
    redirect target (DL-151, DL-152).

    Each group's divergence is divided by tier before anything is asked
    of the operator: a group carrying an editorial divergence is a
    conflict and is reported as a ConflictRow over every divergent
    attribute, while a group whose divergence is measured-only is
    answered by the rule and reported as a SettledRow. No group appears
    on both lists, so a reader counting what was put to the operator and
    what was decided for them counts each group once (DL-325, DL-327,
    DL-329).

    A settled group takes no resolution and cannot abort the run: the
    unresolved abort DL-105 states is reached by an editorial divergence
    with neither a named resolution nor a run-wide on_conflict (DL-328).
    """
    old_to_new_key: dict[str, str] = {}
    conflict_rows: list[ConflictRow] = []
    settled_rows: list[SettledRow] = []
    new_entries: list[tuple[int, EntryRecord]] = []
    entry_patches: list[tuple[EntryRecord, dict[str, str]]] = []
    ambiguous_keys: set[str] = set()
    unresolved = False
    resolutions = resolutions or {}

    for key, members in groups.items():
        contributing_inputs = {idx for idx, _ in members}
        if len(contributing_inputs) == 1:
            idx = next(iter(contributing_inputs))
            if idx != 0:
                new_entries.append(members[0])
            continue

        identity_key = group_identity_key(members)
        divergent_attrs = [
            attr for attr in _TRACKED_ATTRS if len({getattr(r, attr) for _, r in members}) > 1
        ]
        # The divergence is divided before anything is asked of the
        # operator. editorial_attrs is what a person can answer for;
        # measured_attrs is what Traktor measured twice off the one
        # LOCATION, which no operator judgement settles (DL-325).
        #
        # A group carrying at least one editorial name is a conflict
        # exactly as before and carries EVERY divergent attribute in
        # attrs - the measured names included - so its CSV row, its
        # candidates and its resolve rail stand as they stand, and its
        # measured divergence is never reported twice (DL-329).
        editorial_attrs, measured_attrs = metadata_tier.split_by_tier(divergent_attrs)
        settled_by_rule = bool(divergent_attrs) and not editorial_attrs
        # A key naming no group is absent from this lookup, so an unmatched
        # entry is inert rather than an error (DL-105), and a pair naming no
        # member of the group it does name is inert the same way (DL-153):
        # picked stays None and the group falls through below.
        #
        # A settled group takes no resolution: there is nothing to name,
        # and a mapping entry naming one is inert here the way a key
        # naming no group is (DL-105, DL-153).
        pair = resolutions.get(identity_key) if editorial_attrs else None
        picked = next(
            (
                (idx, record)
                for idx, record in members
                if pair is not None and (idx, record.primary_key) == pair
            ),
            None,
        )
        # The label the row and the CSV report carry for a settled group is
        # the pair itself, as "input index:primary key".
        resolution = None if picked is None else "%d:%s" % (picked[0], picked[1].primary_key)
        # Only an editorial divergence can abort. A measured-only one is
        # answered by the rule, so the run assembles where every group
        # the operator was never asked about is the only divergence
        # (DL-325, DL-328).
        if editorial_attrs and resolution is None and on_conflict is None:
            unresolved = True
            conflict_rows.append(
                _metadata_conflict_row(identity_key, divergent_attrs, members, "unresolved")
            )
            continue

        base_members = [(idx, r) for idx, r in members if idx == 0]
        if len(base_members) > 1:
            for idx, record in members:
                if idx != 0:
                    ambiguous_keys.add(record.primary_key)
        # base_members[0] is the record a group holding several base records
        # patches and redirects to; its non-base keys stay ambiguous above,
        # so the reconstruction path still refuses the group (DL-122).
        base_member = base_members[0] if base_members else None

        def pick_non_base() -> tuple[int, EntryRecord]:
            """The non-base copy the run-wide picker names as the survivor,
            which is the answer for the groups no resolution names (DL-108,
            DL-117)."""
            candidates = [(idx, r) for idx, r in members if idx != 0] or members
            policy = on_conflict or "keep-first"
            picker = min if policy == "keep-first" else max
            return picker(candidates, key=lambda m: m[0])

        # The picker exists to answer which of several non-base copies
        # survives, a question that only arises where nothing base-side
        # already occupies the collection slot, so the transplant branch is
        # entered on base_member is None alone (DL-117).
        if base_member is None:
            winner_idx, winner = picked if picked is not None else pick_non_base()
            new_entries.append((winner_idx, winner))
        else:
            winner_idx, winner = base_member
            if picked is not None and picked[1] is not winner:
                # base keeps its entry and the pick is carried by
                # substituting the group's divergent attribute values - and
                # no others (DL-118) - inside that entry's own span.
                _, named_record = picked
                entry_patches.append(
                    (winner, {attr: getattr(named_record, attr) for attr in divergent_attrs})
                )

        for _, record in members:
            if record is not winner:
                old_to_new_key[record.primary_key] = winner.primary_key

        if settled_by_rule:
            # The record whose measured values the output carries, named
            # by the (input index, primary key) pair the branches above
            # already bound: base's own record where the group holds one,
            # because base keeps its entry and no patch is collected for
            # it, and the run-wide picker's winner where it holds none
            # (DL-328). The index travels with it because every member of
            # a settled group carries the one primary key (DL-148).
            settled_rows.append(
                _settled_row(identity_key, measured_attrs, members, winner_idx, winner)
            )
        elif divergent_attrs:
            conflict_rows.append(
                _metadata_conflict_row(
                    identity_key, divergent_attrs, members, resolution or on_conflict
                )
            )

    return ResolvedConflicts(
        old_to_new_key,
        conflict_rows,
        unresolved,
        new_entries,
        ambiguous_keys,
        entry_patches,
        settled_rows,
    )


def _entry_span_text(source_text: str, span_index: SpanIndex, record: EntryRecord) -> str:
    return span_index.span_of(record.entry).text(source_text)


def _apply_replacements(text: str, replacements: list[tuple[int, int, str]]) -> str:
    """Return ``text`` with each ``(start, end, fragment)`` span replaced.

    One forward pass in ascending offset order collects the untouched runs
    and the fragments and joins them once, the shape
    textpatch.apply_text_patches uses, so the document is built once rather
    than rebuilt per replacement. Nothing is mutated mid-loop, so every
    offset keeps reading the text it was measured on and the ordering of
    the caller's list carries no meaning beyond the sort here.

    The spans must be disjoint. A span starting before the previous one's
    end would otherwise contribute an empty run in place of the text
    between them - the slice runs backwards - so the bytes the two spans
    straddle would be dropped and the document silently garbled. It raises
    naming both offsets instead."""
    segments: list[str] = []
    cursor = 0
    for start_at, end_at, fragment in sorted(replacements):
        if start_at < cursor:
            raise ValueError(
                f"overlapping replacement spans: offset {start_at} starts inside "
                f"the span ending at offset {cursor}"
            )
        segments.extend((text[cursor:start_at], fragment))
        cursor = end_at
    segments.append(text[cursor:])
    return "".join(segments)


def assemble_output(
    base_source: str,
    base_root: ET.Element,
    contributions: list[tuple[str, ET.Element]],
    confidence: MatchConfidence,
    on_conflict: Optional[str] = None,
    reconstruct: bool = False,
    *,
    resolutions: Optional[dict[str, tuple[int, str]]] = None,
) -> SpliceResult:
    """Merge every contribution into base_source: build cross-input
    identity groups, resolve conflicts (aborting with zero output on any
    unresolved one), transplant surviving collection entries as verbatim
    spans, then hand off to playlist import for the PLAYLISTS tree
    (DL-007, DL-008).

    resolutions maps an identity-group key to an (input index, primary key)
    pair naming one record of that group, and settles that group alone. An empty mapping leaves every group to on_conflict,
    which is what the parameter's absence leaves them to, so the bytes a
    call with an empty mapping produces are the bytes a call omitting it
    produces (DL-104).

    The result's settled_rows are the groups the tier answered, reported
    whatever the run's outcome: the groups the rule settled are part of
    what the run did, and an aborted run is still a run whose measured
    divergences were never put to the operator (DL-008's precedent,
    DL-329). No entry patch is collected for them - a settled group is
    named by no resolution, so base's own measured numbers stand where
    the group holds a base record and the picked non-base record's span
    is transplanted whole where it does not (DL-328)."""
    inputs = [base_root] + [root for _, root in contributions]
    sources = [base_source] + [text for text, _ in contributions]
    records_by_input = [collection_records(root) for root in inputs]

    # One SpanIndex per input source, built once here rather than once per
    # entry or per playlist, so a merge scans each source once regardless
    # of how many entries and playlists it contributes.
    span_indexes = [SpanIndex(sources[i], inputs[i]) for i in range(len(inputs))]

    groups = group_identities(records_by_input, confidence)
    resolved = _resolve_conflicts(groups, on_conflict, resolutions=resolutions)
    old_to_new_key, conflict_rows, unresolved, new_entries_records, ambiguous_keys = resolved
    settled_rows = resolved.settled_rows

    stats = {
        "inputs_merged": len(contributions),
        "identity_groups": len(groups),
        "conflicts_reported": len(conflict_rows),
        # How many groups the tier answered, and how many of those are
        # worth reading. Read off settled_rows rather than counted a
        # second time anywhere above, so the CLI's printed count, the
        # preview's sentence and the rows behind them are the one set
        # (DL-215, DL-331).
        "groups_settled_by_rule": len(settled_rows),
        "settled_groups_outlying": sum(1 for row in settled_rows if row.is_outlier),
        "collection_entries_added": 0,
        "playlists_imported": 0,
        "playlists_renamed": 0,
        "sorting_info_dropped": [],
        "playlists_reconstructed": 0,
        "playlists_skipped_reconstructed": 0,
        "reconstructed_playlists": {},
        # The three counts a reconstruction run is read by: how many base
        # playlists held nothing before it, how many of those it filled,
        # and the names of the ones it could not. A caller reporting the
        # run reads them off the run rather than re-walking the base
        # collection, which is the same reason reconstructed_playlists is
        # carried here. Zero and empty for a run with reconstruct off,
        # because that run fills no playlist rather than filling none of
        # none.
        "empty_playlists": 0,
        "refilled_playlists": 0,
        "unfilled_playlists": [],
        # Playlist entries placed on a track the collection holds more
        # than once, in total and per playlist. Reported rather than
        # refused: the entry resolves to the record the merge itself
        # redirects that key to, and a run that refuses every playlist
        # over a handful of duplicated tracks answers nothing the
        # operator can act on (DL-230).
        "entries_on_duplicated_tracks": 0,
        "playlists_on_duplicated_tracks": {},
        # The COLLECTION ENTRIES count the output carries. Read with
        # collection_entries_added, it gives the count the collection held
        # before the run without a second parse of the base text.
        "collection_entries_total": 0,
    }

    if unresolved:
        return SpliceResult(
            output=None,
            stats=stats,
            conflict_rows=conflict_rows,
            settled_rows=settled_rows,
            errors=["unresolved_conflicts"],
        )

    # New collection entries: transplant each winner's own ENTRY span from
    # its originating input, verbatim (collection entries are never renamed).
    new_entry_texts = [
        _entry_span_text(sources[idx], span_indexes[idx], record) for idx, record in new_entries_records
    ]
    stats["collection_entries_added"] = len(new_entry_texts)

    # Every primary key the assembled output holds a collection entry for:
    # base's own surviving records plus the entries this run transplants.
    # A playlist ENTRY pointing outside this set names a track no
    # collection in the run holds - a reference the source files were
    # already carrying broken - and the passes below drop it from the
    # playlist that carries it and count it, rather than refusing an
    # output over it (DL-232).
    valid_keys = {r.primary_key for r in records_by_input[0]} | {r.primary_key for _, r in new_entries_records}
    dropped_refs: list[tuple[str, str]] = []
    # A resolvable key that left because the ENTRY carrying it was
    # removed for a second, unresolvable key on the same entry. Empty in
    # every ordinary run - a Traktor playlist entry names one track - and
    # reported rather than dropped silently, because losing a track the
    # collection does hold is the thing this tool exists to undo.
    carried_away: list[tuple[str, str]] = []

    # One replacement list over base_source, seeded with the source picks'
    # entry patches and extended below by the reconstruction block's rebuilt
    # playlists. Every offset in it is measured by span_indexes[0] against
    # the original base_source, and a COLLECTION span and a PLAYLISTS span
    # are disjoint, so one forward pass below the block - which collects
    # segments and never mutates the text mid-loop - leaves every offset
    # reading the text it was measured on. The list is declared here
    # rather than inside the block because a run carrying entry patches and
    # no reconstruction must still reach the apply (DL-121).
    replacements: list[tuple[int, int, str]] = []
    for base_record, values in resolved.entry_patches:
        span = span_indexes[0].span_of(base_record.entry)
        replacements.append(
            (span.start, span.end, patch_entry_attributes(span.text(base_source), values))
        )

    # Reconstruction pre-pass: a base playlist whose redirected key
    # sequence differs from the incoming playlist at the same folder path
    # is rebuilt in place from the union of all of them, keeping base's
    # own NODE, UUID and folder position. Runs here because old_to_new_key exists by this
    # line and no builder call has consumed a span yet, so rewriting
    # base_source and re-parsing is still free (DL-096).
    reconstructed: dict[str, int] = {}
    # Entries the rebuilds added, as against the entries they hold: the
    # two differ by whatever a non-empty rebuilt playlist already carried.
    entries_added = 0
    matched: set[str] = set()
    # The spans the pre-pass rebuilds, so the drop pass below leaves them
    # to it: a rebuilt playlist was already filtered against valid_keys
    # and a second patch over the same span would collide with the first.
    #
    # Keyed by span start rather than by id(element). Under lxml an
    # element is a transient proxy, and once nothing references it the
    # proxy is collected and its address can be reused by an unrelated
    # one - the hazard SpanIndex documents and defends against by
    # retaining every element it walks. Keying on an offset needs no such
    # defence and no dependency on another object staying alive.
    rebuilt_spans: set[int] = set()
    if reconstruct:
        # Playlists pair by the folder path they sit at, which is the
        # identity Traktor's own SORTING_INFO PATH gives them, not by
        # bare NAME. A real collection reuses a name freely across
        # folders: one measured 1187-playlist collection holds them under
        # 768 distinct names and 1187 distinct paths, so 303 of its names
        # are held by two or more playlists that are not the same
        # playlist. Keying by name called every one of those ambiguous
        # and refused the whole run (DL-228).
        base_by_path: dict[str, list] = {}
        for path, node in playlist_path_pairs(base_root):
            base_by_path.setdefault(path, []).append(node)
        incoming_by_path: dict[str, list] = {}
        incoming_by_name: dict[str, list] = {}
        incoming_dupes: set[str] = set()
        for _, root in contributions:
            paths_here: dict[str, int] = {}
            for path, node in playlist_path_pairs(root):
                incoming_by_path.setdefault(path, []).append(node)
                incoming_by_name.setdefault(
                    node.attrib.get("NAME", ""), []
                ).append(node)
                paths_here[path] = paths_here.get(path, 0) + 1
            # Counted per contribution, not across them: one path appearing
            # in several --input files is the fold DL-092 asks for, while
            # the same path twice inside one file has no single playlist to
            # reconstruct from (DL-098).
            incoming_dupes |= {p for p, count in paths_here.items() if count > 1}

        # A PATH occurring more than once on either side has no single
        # playlist to reconstruct or to reconstruct from, so it aborts
        # rather than picking one by document order (DL-098). Matching is
        # exact and case-sensitive, so paths differing only in case are
        # distinct playlists and never pair up.
        duplicate_paths = sorted(
            {path for path, nodes in base_by_path.items() if len(nodes) > 1 and path in incoming_by_path}
            | {path for path in incoming_dupes if path in base_by_path}
        )
        if duplicate_paths:
            conflict_rows.extend(
                ConflictRow(path, "playlist_name", "ambiguous") for path in duplicate_paths
            )
            return SpliceResult(
                output=None, stats=stats, conflict_rows=conflict_rows,
                settled_rows=settled_rows,
                errors=[f"ambiguous_playlist_name playlist={path}" for path in duplicate_paths],
            )

        # How many base playlists carry each bare name, for the fallback
        # below: a playlist that moved to another folder between the two
        # collections has no counterpart at its own path, and its name is
        # the only other thing that identifies it.
        base_name_counts: dict[str, int] = {}
        for nodes in base_by_path.values():
            for node in nodes:
                name = node.attrib.get("NAME", "")
                base_name_counts[name] = base_name_counts.get(name, 0) + 1

        # The base playlists holding nothing before this run: a path whose
        # redirected key sequence is empty. Measured before the loop below
        # rebuilds any of them, because after the rebuild every filled one
        # holds keys and the set would read empty.
        empty_names = {
            path
            for path, nodes in base_by_path.items()
            if not redirected_playlist_keys(nodes[0], old_to_new_key)
        }

        # path -> how many of its rebuilt entries resolve to a track the
        # base holds more than once.
        on_duplicated: dict[str, int] = {}
        for path, base_nodes in base_by_path.items():
            base_node = base_nodes[0]
            name = base_node.attrib.get("NAME", "")
            incoming_nodes = incoming_by_path.get(path)
            if not incoming_nodes:
                # No counterpart at that path. A playlist that moved
                # folders is still the same playlist, so it pairs on its
                # name where that name names exactly one playlist on each
                # side; where it does not, there is nothing that says
                # which of them this is, and it is left alone rather than
                # rebuilt from a guess.
                by_name = incoming_by_name.get(name, [])
                if base_name_counts.get(name) != 1 or len(by_name) != 1:
                    continue
                incoming_nodes = by_name
            base_keys = redirected_playlist_keys(base_node, old_to_new_key)
            # Compared against the incoming side's own ordered union rather
            # than against the merged result: merging puts base first, so a
            # merged sequence can never differ from base whenever the two
            # hold the same tracks, and an ordering difference would be
            # structurally invisible (DL-091).
            incoming_keys: list = []
            for node in incoming_nodes:
                for key in redirected_playlist_keys(node, old_to_new_key):
                    if key not in incoming_keys:
                        incoming_keys.append(key)
            if base_keys == incoming_keys:
                # Identical ordered contents: base's bytes stay untouched,
                # and the incoming copy is dropped rather than imported -
                # a '<name> (2)' holding exactly what base already holds is
                # the duplicate reconstruction exists to prevent, so a
                # matched playlist is skipped whether or not it needed
                # rebuilding (DL-093). Recorded by name, because the
                # import pass below reads the names an incoming playlist
                # carries rather than the path it came from.
                matched.add(name)
                continue
            merged = merged_playlist_entries(base_node, incoming_nodes, old_to_new_key)
            unresolvable = [key for key in merged if key not in valid_keys]
            if unresolvable:
                dropped_refs.extend((path, key) for key in unresolvable)
                merged = [key for key in merged if key in valid_keys]

            # An incoming entry whose identity group holds more than one
            # base record has no single right redirect target, and it is
            # placed on the one the merge already redirects that key to -
            # base_members[0] - rather than dropped or refused. Dropping
            # it loses a track from a playlist this run exists to rebuild;
            # refusing loses every playlist. Both are worse answers than
            # placing it on a record the collection holds for that same
            # track and saying how many were placed that way (DL-094,
            # DL-122, DL-230).
            redirected_here = {
                old_to_new_key.get(raw, raw)
                for node in incoming_nodes
                for pk in node_primary_keys(node)
                for raw in (pk.attrib.get("KEY", ""),)
                if raw in ambiguous_keys
            }
            placed = sum(1 for key in merged if key in redirected_here)
            if placed:
                on_duplicated[path] = placed
                conflict_rows.extend(
                    ConflictRow(key, "ambiguous_redirect", "placed_on_first")
                    for key in sorted(redirected_here)
                )

            playlist_elem = base_node.find("PLAYLIST")
            if playlist_elem is None:
                continue
            rebuilt = ET.fromstring(ET.tostring(playlist_elem))
            for child in list(rebuilt):
                rebuilt.remove(child)
            for key in merged:
                entry = ET.SubElement(rebuilt, "ENTRY")
                ET.SubElement(entry, "PRIMARYKEY", {"TYPE": "TRACK", "KEY": key})
            rebuilt.attrib["ENTRIES"] = str(len(merged))
            span = span_indexes[0].span_of(playlist_elem)
            rebuilt_spans.add(span.start)
            replacements.append((span.start, span.end, ET.tostring(rebuilt, encoding="unicode")))
            reconstructed[path] = len(merged)
            # What the rebuild put there that base did not already hold.
            # A rebuilt playlist that was not empty keeps its own entries
            # and gains the rest, so its whole contents are what it holds
            # and only the remainder is what this run added. Counting the
            # contents as additions would credit the run with entries the
            # operator already had (DL-215, DL-238).
            held_before = set(base_keys)
            entries_added += sum(1 for key in merged if key not in held_before)
            matched.add(name)

    # A base playlist this run does not rebuild can still carry a
    # reference to a track no collection holds. It is patched in place,
    # dropping the unresolvable entries alone and keeping its NODE, UUID,
    # name and folder position; the whole ENTRY goes, so anything else
    # that entry carried goes with it (DL-232).
    for node in find_playlist_nodes(base_root):
        playlist_elem = node.find("PLAYLIST")
        if playlist_elem is None:
            continue
        if span_indexes[0].span_of(playlist_elem).start in rebuilt_spans:
            continue
        # Walked once, and the copy below is paid for only where the walk
        # found something to drop: a base playlist holding nothing
        # unresolvable keeps its own bytes, which is most of them.
        #
        # Read as the keys stand, which is the same question
        # drop_unresolvable_entries asks of the same untouched element
        # below. Redirecting them here would put the guard in one key
        # space and the work it gates in another, and the guard would
        # then be true in exactly the state where the dropper had
        # something to do (DL-189).
        if all(
            pk.attrib.get("KEY", "") in valid_keys for pk in node_primary_keys(node)
        ):
            continue
        trimmed = ET.fromstring(ET.tostring(playlist_elem))
        name = node.attrib.get("NAME", "")
        dropped = drop_unresolvable_entries(trimmed, valid_keys)
        dropped_refs.extend((name, key) for key in dropped.unresolvable)
        carried_away.extend((name, key) for key in dropped.carried_away)
        span = span_indexes[0].span_of(playlist_elem)
        replacements.append((span.start, span.end, ET.tostring(trimmed, encoding="unicode")))

    # Applied below both of the block's aborts, which return with output
    # None: a refused run discards its entry patches with everything else
    # and no rewritten base_source reaches an output (DL-121).
    # _apply_replacements makes one forward pass over the original
    # base_source, which is the text span_indexes[0] measured every offset
    # on, and enforces the disjointness of the COLLECTION and PLAYLISTS
    # spans rather than assuming it. The re-parse is guarded on the
    # combined list rather than the reconstruction's own, because the
    # COLLECTION ENTRIES count is read from base_root below. span_indexes[0]
    # is stale from here on and no base-side span lookup follows it; the
    # contribution lookups below read index one and above.
    if replacements:
        base_source = _apply_replacements(base_source, replacements)
        base_root = parse_xml_bytes(base_source.encode("utf-8"))

    stats["playlists_reconstructed"] = len(reconstructed)
    stats["playlist_entries_added"] = entries_added
    if reconstruct:
        stats["entries_on_duplicated_tracks"] = sum(on_duplicated.values())
        stats["playlists_on_duplicated_tracks"] = dict(sorted(on_duplicated.items()))
        # An empty name the run rebuilt is filled; one it did not is
        # unfilled, and it keeps its name and stays empty. The two are
        # read off the one set measured before the rebuild, so a name
        # cannot be counted in both.
        stats["empty_playlists"] = len(empty_names)
        stats["refilled_playlists"] = len(empty_names & set(reconstructed))
        stats["unfilled_playlists"] = sorted(empty_names - set(reconstructed))
    # Folder paths and resulting entry counts, so a caller can report
    # which playlists a run rebuilt without recomputing the comparison the
    # pre-pass already made, and can tell two playlists sharing a name
    # apart when it does.
    stats["reconstructed_playlists"] = dict(sorted(reconstructed.items()))

    output = base_source
    collection_span = find_element_span(output, "COLLECTION")
    if collection_span is None:
        return SpliceResult(
            output=None,
            stats=stats,
            conflict_rows=conflict_rows,
            settled_rows=settled_rows,
            errors=["no_collection"],
        )

    # The count the COLLECTION element declares and the count the stats
    # report are one number read once, so a caller reporting the run's
    # size reports what the output says rather than a second sum of the
    # same two terms.
    collection_total = len(collection_entries(base_root)) + len(new_entry_texts)
    stats["collection_entries_total"] = collection_total

    builder = OutputBuilder()
    builder.add_verbatim(output[: collection_span.start])
    builder.add_counted_span(
        output, collection_span, "COLLECTION", "ENTRIES", new_entry_texts,
        count=collection_total,
    )

    # Import every non-base playlist as a flattened child of the base root folder.
    # Walked once and held: the self-check below reads the same tree at
    # the same revision, and nothing between here and there changes it.
    # Holding the list also keeps every element's lxml proxy alive for as
    # long as the walk's results are in use.
    base_playlist_nodes = find_playlist_nodes(base_root)
    existing_names = {node.attrib.get("NAME", "") for node in base_playlist_nodes}
    # A reconstructed name is skipped below rather than renamed, so it
    # is left out of the in-use set the rename rule consults.
    existing_names -= matched
    playlist_fragments: list[str] = []
    sorting_info_fragments: list[str] = []
    sorting_info_dropped: list[str] = []
    unresolved_refs: list[tuple[str, str]] = []
    # (playlist name, key) for every key the imported fragments carry.
    emitted_playlist_keys: list[tuple[str, str]] = []
    renamed_count = 0
    skipped_reconstructed = 0
    for contribution_idx, (source_text, root) in enumerate(contributions, start=1):
        result = import_playlists(
            source_text, root, old_to_new_key, existing_names,
            span_indexes[contribution_idx], valid_keys,
        )
        for imported in result.playlists:
            # A reconstructed playlist already carries this incoming one's
            # entries inside base's own node, so importing it as well would
            # append the '<name> (2)' duplicate reconstruction exists to
            # avoid (DL-093). Its SORTING_INFO goes with it: base's own
            # entry for that name already governs the surviving node
            # (DL-099).
            if imported.original_name in matched:
                skipped_reconstructed += 1
                continue
            playlist_fragments.append(imported.fragment)
            # Only what the self-check below would report. In a run
            # where the three passes did their work this stays empty,
            # rather than holding one tuple per entry of every imported
            # playlist to be scanned and found clean.
            emitted_playlist_keys.extend(
                (imported.final_name, key)
                for key in imported.primary_keys
                if key not in valid_keys
            )
            if imported.final_name != imported.original_name:
                # Counted per surviving fragment rather than from
                # result.renamed, which also counts a rename applied to a
                # playlist that is then skipped as matched - a rename the
                # output does not contain and the operator cannot see.
                renamed_count += 1
        sorting_info_fragments.extend(result.sorting_info)
        sorting_info_dropped.extend(result.dropped_sorting_info)
        # Only a surviving fragment's drops are the operator's: a playlist
        # skipped as already reconstructed is not in the output, and the
        # base node that replaced it reported its own.
        skipped = {p.original_name for p in result.playlists if p.original_name in matched}
        dropped_refs.extend(
            (name, key) for name, key in result.dropped_refs if name not in skipped
        )
        carried_away.extend(
            (name, key) for name, key in result.carried_away if name not in skipped
        )
    stats["playlists_imported"] = len(playlist_fragments)
    stats["playlists_renamed"] = renamed_count
    stats["playlists_skipped_reconstructed"] = skipped_reconstructed
    stats["sorting_info_dropped"] = list(sorting_info_dropped)

    # The playlist entries that named a track no collection in the run
    # holds. Each was dropped from the playlist carrying it by one of the
    # three passes above, and is reported here: the reference was already
    # broken in the files this run read, so refusing an output over it
    # would discard every playlist the run rebuilt to preserve a pointer
    # to nothing (DL-232). The track count is the distinct keys, which is
    # far smaller than the entry count whenever one missing track sits in
    # several playlists.
    stats["entries_dropped_unresolvable"] = len(dropped_refs)
    stats["tracks_dropped_unresolvable"] = len({key for _, key in dropped_refs})
    stats["playlists_with_dropped_entries"] = dict(
        sorted(Counter(name for name, _ in dropped_refs).items())
    )
    # Normally empty; a caller that finds it filled has lost a track the
    # collection holds, and the key names which.
    stats["entries_carried_away"] = [key for _, key in carried_away]

    subnodes_span = find_element_span(output, "SUBNODES")
    if subnodes_span is None:
        return SpliceResult(
            output=None,
            stats=stats,
            conflict_rows=conflict_rows,
            settled_rows=settled_rows,
            errors=["no_root_subnodes"],
        )
    root_subnodes_elem = base_root.find(".//PLAYLISTS/NODE/SUBNODES")
    original_root_count = 0 if root_subnodes_elem is None else len(list(root_subnodes_elem))

    indexing_span = find_element_span(output, "INDEXING", start_from=subnodes_span.end)
    if indexing_span is None and sorting_info_fragments:
        return SpliceResult(
            output=None,
            stats=stats,
            conflict_rows=conflict_rows,
            settled_rows=settled_rows,
            errors=["no_indexing"],
        )

    builder.add_verbatim(output[collection_span.end: subnodes_span.start])
    builder.add_counted_span(
        output, subnodes_span, "SUBNODES", "COUNT", playlist_fragments,
        count=original_root_count + len(playlist_fragments),
    )
    if indexing_span is None:
        builder.add_verbatim(output[subnodes_span.end:])
    else:
        builder.add_verbatim(output[subnodes_span.end: indexing_span.start])
        builder.add_children_span(output, indexing_span, "INDEXING", sorting_info_fragments)
        builder.add_verbatim(output[indexing_span.end:])
    output = builder.build()

    # Every PRIMARYKEY the run emits resolves to a collection entry the
    # output holds. The three passes above drop the ones that do not -
    # from a rebuilt playlist, from a base playlist left in place, and
    # from an imported fragment - so a reference standing here is one no
    # pass reached, which is this module's own defect and not the
    # operator's collection. It is reported as a refusal rather than
    # asserted, because every other way this function declines to write
    # is a refusal a caller can print, and a defect that reaches an
    # operator should refuse the write rather than end the process.
    #
    # Read off what was emitted: base_root re-parsed from the patched
    # source, and the keys each import recorded as it walked the node it
    # serialised, rather than off the unpatched inputs the drops were
    # made against. Parsing the fragments back would re-parse every
    # imported playlist to recover what the import already knew.
    for node in base_playlist_nodes:
        name = node.attrib.get("NAME", "")
        for pk in node_primary_keys(node):
            if pk.attrib.get("KEY", "") not in valid_keys:
                unresolved_refs.append((name, pk.attrib.get("KEY", "")))
    unresolved_refs.extend(emitted_playlist_keys)

    if unresolved_refs:
        errors = [f"unresolved_reference playlist={name} key={key}" for name, key in unresolved_refs]
        return SpliceResult(
            output=None,
            stats=stats,
            conflict_rows=conflict_rows,
            settled_rows=settled_rows,
            errors=errors,
        )

    # Validate: the merge introduces no second entry for a LOCATION the
    # merged COLLECTION already holds. The primary key IS the location
    # (volume + dir + file), so a transplanted entry whose key base already
    # carries, or two transplants sharing one key, is the pair of entries
    # for one file that DL-004 forbids - and the shape a source resolution
    # produced while it transplanted the winner's ENTRY beside base's own.
    #
    # Read off the records the merge already holds rather than by parsing
    # the assembled output, which would cost a second parse of the largest
    # file in the run. base's own keys are unaffected by the entry patches:
    # a patch substitutes values from _TRACKED_ATTRS, and no location field
    # is among them. A base that already carries two entries for one file is
    # its own input's condition and is left to it; only what this run adds
    # is judged here.
    base_keys = {record.primary_key for record in records_by_input[0]}
    added: dict[str, int] = {}
    for _, record in new_entries_records:
        added[record.primary_key] = added.get(record.primary_key, 0) + 1
    collisions = sorted(
        key for key, count in added.items() if key in base_keys or count > 1
    )
    if collisions:
        return SpliceResult(
            output=None,
            stats=stats,
            conflict_rows=conflict_rows,
            settled_rows=settled_rows,
            errors=[f"entry_location_collision key={key}" for key in collisions],
        )

    # Validate: the replacement pass moved no base ENTRY. It rewrites
    # attribute values inside a base entry's own span and rebuilds playlist
    # nodes, so the COLLECTION it re-parses holds the entries base held; a
    # different count means a span was applied over an element boundary.
    reparsed = len(collection_entries(base_root))
    if reparsed != len(records_by_input[0]):
        return SpliceResult(
            output=None,
            stats=stats,
            conflict_rows=conflict_rows,
            settled_rows=settled_rows,
            errors=[
                f"collection_entry_count base={len(records_by_input[0])} assembled={reparsed}"
            ],
        )

    # Validate: every PRIMARYKEY the assembled text emits names an entry the
    # assembled COLLECTION holds. The pass above answers the same question
    # from the inputs and the redirect mapping - what the keys OUGHT to be -
    # so it cannot see a fragment emitted carrying something else. This one
    # reads what the run is about to return, which is the artefact the
    # operator gets.
    #
    # Defence in depth rather than a repair: no run reaching here is known to
    # emit a key the pass above admits, and this was not added on the
    # strength of one. It is a scan of a string the run already holds, and
    # the emit path is where a redirect that went wrong would show.
    # Both sides are unescaped before they are compared, because the two
    # are not written by the same hand: a LOCATION carried through
    # verbatim keeps whatever escaping its own file used, while a
    # PRIMARYKEY inside a re-serialised playlist carries the escaping the
    # serialiser chose. A file name holding a tab reaches this check as a
    # literal tab on one side and as `&#9;` on the other, and a name
    # holding an ampersand the same way - the same value, written twice,
    # read as two values and reported as a key naming no entry (DL-231).
    collection_text = output.split("</COLLECTION>")[0]
    emitted_entries = {
        html.unescape(f"{volume}{dir_value}{file_name}")
        for dir_value, file_name, volume in _EMITTED_LOCATION_RE.findall(collection_text)
    }
    unresolved_emitted = sorted(
        {
            key
            for raw in _EMITTED_KEY_RE.findall(output)
            for key in (html.unescape(raw),)
            if key not in emitted_entries
        }
    )
    if unresolved_emitted:
        return SpliceResult(
            output=None,
            stats=stats,
            conflict_rows=conflict_rows,
            settled_rows=settled_rows,
            errors=[f"emitted_key_unresolved key={key}" for key in unresolved_emitted],
        )

    return SpliceResult(
        output=output,
        stats=stats,
        conflict_rows=conflict_rows,
        settled_rows=settled_rows,
        errors=[],
    )
