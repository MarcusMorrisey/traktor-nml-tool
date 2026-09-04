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

from dataclasses import dataclass, field
from typing import Optional

from .confidence import MatchConfidence
from .matching import record_keys
from .model import EntryRecord, collection_entries, collection_records
from .playlists import (
    find_playlist_nodes,
    import_playlists,
    merged_playlist_entries,
    node_primary_keys,
    redirected_playlist_keys,
)
from .spans import OutputBuilder, SpanIndex, find_element_span
from .textpatch import patch_entry_attributes
from .xmlio import ET, parse_xml_bytes

_TRACKED_ATTRS = ("artist", "title", "album", "filesize", "playtime_float", "bitrate")


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
    """

    identity_key: str
    attrs: str
    resolution: str
    member_keys: frozenset[str] = frozenset()
    candidates: tuple[ConflictCandidate, ...] = ()


@dataclass
class SpliceResult:
    """output is None exactly when errors is non-empty - an abort with
    nothing written (extending DL-012's validate-before-write invariant
    to a multi-input merge); conflict_rows is populated on every run
    regardless of outcome, even a clean one (DL-008)."""
    output: Optional[str]
    stats: dict[str, object]
    conflict_rows: list[ConflictRow] = field(default_factory=list)
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
    positionally, carrying entry_patches as a named attribute.

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
    ) -> "ResolvedConflicts":
        self = super().__new__(
            cls, (old_to_new_key, conflict_rows, unresolved, new_entries, ambiguous_keys)
        )
        self.entry_patches = entry_patches
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
    """
    old_to_new_key: dict[str, str] = {}
    conflict_rows: list[ConflictRow] = []
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
        # A key naming no group is absent from this lookup, so an unmatched
        # entry is inert rather than an error (DL-105), and a pair naming no
        # member of the group it does name is inert the same way (DL-153):
        # picked stays None and the group falls through below.
        pair = resolutions.get(identity_key) if divergent_attrs else None
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
        if divergent_attrs and resolution is None and on_conflict is None:
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

        if divergent_attrs:
            conflict_rows.append(
                _metadata_conflict_row(
                    identity_key, divergent_attrs, members, resolution or on_conflict
                )
            )

    return ResolvedConflicts(
        old_to_new_key, conflict_rows, unresolved, new_entries, ambiguous_keys, entry_patches
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
    produces (DL-104)."""
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

    stats = {
        "inputs_merged": len(contributions),
        "identity_groups": len(groups),
        "conflicts_reported": len(conflict_rows),
        "collection_entries_added": 0,
        "playlists_imported": 0,
        "playlists_renamed": 0,
        "sorting_info_dropped": [],
        "playlists_reconstructed": 0,
        "playlists_skipped_reconstructed": 0,
        "reconstructed_playlists": {},
    }

    if unresolved:
        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=["unresolved_conflicts"])

    # New collection entries: transplant each winner's own ENTRY span from
    # its originating input, verbatim (collection entries are never renamed).
    new_entry_texts = [
        _entry_span_text(sources[idx], span_indexes[idx], record) for idx, record in new_entries_records
    ]
    stats["collection_entries_added"] = len(new_entry_texts)

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
    # sequence differs from the same-named incoming ones is rebuilt in
    # place from the union of all of them, keeping base's own NODE, UUID
    # and folder position. Runs here because old_to_new_key exists by this
    # line and no builder call has consumed a span yet, so rewriting
    # base_source and re-parsing is still free (DL-096).
    reconstructed: dict[str, int] = {}
    matched: set[str] = set()
    if reconstruct:
        base_nodes_by_name: dict[str, list] = {}
        for node in find_playlist_nodes(base_root):
            base_nodes_by_name.setdefault(node.attrib.get("NAME", ""), []).append(node)
        incoming_by_name: dict[str, list] = {}
        incoming_dupes: set[str] = set()
        for _, root in contributions:
            names_here: dict[str, int] = {}
            for node in find_playlist_nodes(root):
                name = node.attrib.get("NAME", "")
                incoming_by_name.setdefault(name, []).append(node)
                names_here[name] = names_here.get(name, 0) + 1
            # Counted per contribution, not across them: one name appearing
            # in several --input files is the fold DL-092 asks for, while
            # the same name twice inside one file has no single playlist to
            # reconstruct from (DL-098).
            incoming_dupes |= {n for n, count in names_here.items() if count > 1}

        # A NAME occurring more than once on either side has no single
        # playlist to reconstruct or to reconstruct from, so it aborts
        # rather than picking one by document order (DL-098). Matching is
        # exact and case-sensitive, so names differing only in case are
        # distinct playlists and never pair up.
        duplicate_names = sorted(
            {name for name, nodes in base_nodes_by_name.items() if len(nodes) > 1 and name in incoming_by_name}
            | {name for name in incoming_dupes if name in base_nodes_by_name}
        )
        if duplicate_names:
            conflict_rows.extend(
                ConflictRow(name, "playlist_name", "ambiguous") for name in duplicate_names
            )
            return SpliceResult(
                output=None, stats=stats, conflict_rows=conflict_rows,
                errors=[f"ambiguous_playlist_name playlist={name}" for name in duplicate_names],
            )

        ambiguous_hits: list[tuple[str, str]] = []
        for name, base_nodes in base_nodes_by_name.items():
            incoming_nodes = incoming_by_name.get(name)
            if not incoming_nodes:
                continue
            base_node = base_nodes[0]
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
                # matched name is skipped whether or not it needed
                # rebuilding (DL-093).
                matched.add(name)
                continue
            merged = merged_playlist_entries(base_node, incoming_nodes, old_to_new_key)

            for node in incoming_nodes:
                for pk in node_primary_keys(node):
                    raw = pk.attrib.get("KEY", "")
                    if raw in ambiguous_keys:
                        ambiguous_hits.append((name, raw))
            if ambiguous_hits:
                continue

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
            replacements.append((span.start, span.end, ET.tostring(rebuilt, encoding="unicode")))
            reconstructed[name] = len(merged)
            matched.add(name)

        if ambiguous_hits:
            conflict_rows.extend(
                ConflictRow(key, "ambiguous_redirect", "ambiguous") for _, key in ambiguous_hits
            )
            return SpliceResult(
                output=None, stats=stats, conflict_rows=conflict_rows,
                errors=[f"ambiguous_redirect playlist={name} key={key}" for name, key in ambiguous_hits],
            )

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
    # Names and resulting entry counts, so a caller can report which
    # playlists a run rebuilt without recomputing the comparison the
    # pre-pass already made.
    stats["reconstructed_playlists"] = dict(sorted(reconstructed.items()))

    output = base_source
    collection_span = find_element_span(output, "COLLECTION")
    if collection_span is None:
        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=["no_collection"])

    builder = OutputBuilder()
    builder.add_verbatim(output[: collection_span.start])
    builder.add_counted_span(
        output, collection_span, "COLLECTION", "ENTRIES", new_entry_texts,
        count=len(collection_entries(base_root)) + len(new_entry_texts),
    )

    # Import every non-base playlist as a flattened child of the base root folder.
    existing_names = {node.attrib.get("NAME", "") for node in find_playlist_nodes(base_root)}
    # A reconstructed name is skipped below rather than renamed, so it
    # is left out of the in-use set the rename rule consults.
    existing_names -= matched
    playlist_fragments: list[str] = []
    sorting_info_fragments: list[str] = []
    sorting_info_dropped: list[str] = []
    unresolved_refs: list[tuple[str, str]] = []
    renamed_count = 0
    skipped_reconstructed = 0
    for contribution_idx, (source_text, root) in enumerate(contributions, start=1):
        result = import_playlists(
            source_text, root, old_to_new_key, existing_names, span_indexes[contribution_idx]
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
            if imported.final_name != imported.original_name:
                # Counted per surviving fragment rather than from
                # result.renamed, which also counts a rename applied to a
                # playlist that is then skipped as matched - a rename the
                # output does not contain and the operator cannot see.
                renamed_count += 1
        sorting_info_fragments.extend(result.sorting_info)
        sorting_info_dropped.extend(result.dropped_sorting_info)
    stats["playlists_imported"] = len(playlist_fragments)
    stats["playlists_renamed"] = renamed_count
    stats["playlists_skipped_reconstructed"] = skipped_reconstructed
    stats["sorting_info_dropped"] = list(sorting_info_dropped)

    subnodes_span = find_element_span(output, "SUBNODES")
    if subnodes_span is None:
        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=["no_root_subnodes"])
    root_subnodes_elem = base_root.find(".//PLAYLISTS/NODE/SUBNODES")
    original_root_count = 0 if root_subnodes_elem is None else len(list(root_subnodes_elem))

    indexing_span = find_element_span(output, "INDEXING", start_from=subnodes_span.end)
    if indexing_span is None and sorting_info_fragments:
        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=["no_indexing"])

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

    # Validate: every PRIMARYKEY in the assembled playlist tree resolves to
    # a surviving collection entry, aborting and naming each unresolved
    # reference by playlist and key (checked against the parsed base tree's
    # own keys plus the newly added entries; imported fragments were
    # already redirected against old_to_new_key by import_playlists).
    valid_keys = {r.primary_key for r in records_by_input[0]} | {r.primary_key for _, r in new_entries_records}
    for node in find_playlist_nodes(base_root):
        name = node.attrib.get("NAME", "")
        for pk in node_primary_keys(node):
            if pk.attrib.get("KEY", "") not in valid_keys:
                unresolved_refs.append((name, pk.attrib.get("KEY", "")))
    for source_text, root in contributions:
        for node in find_playlist_nodes(root):
            name = node.attrib.get("NAME", "")
            for pk in node_primary_keys(node):
                old_key = pk.attrib.get("KEY", "")
                effective_key = old_to_new_key.get(old_key, old_key)
                if effective_key not in valid_keys:
                    unresolved_refs.append((name, old_key))

    if unresolved_refs:
        errors = [f"unresolved_reference playlist={name} key={key}" for name, key in unresolved_refs]
        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=errors)

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
            errors=[
                f"collection_entry_count base={len(records_by_input[0])} assembled={reparsed}"
            ],
        )

    return SpliceResult(output=output, stats=stats, conflict_rows=conflict_rows, errors=[])
