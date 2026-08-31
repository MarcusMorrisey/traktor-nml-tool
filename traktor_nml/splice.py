"""Merge a base NML with further NML files while every playlist stays valid.

Scope note (v1, see the plan's tradeoffs): the base input is authoritative
for its own COLLECTION and playlists - its bytes are never rewritten. Track
identity across inputs uses the shared record_keys tier ordering, cascaded
through every tier via union-find (not just each record's own top-tier key)
so two copies of one track that happen to agree on a lower tier but not the
top one still land in the same identity group, since splice needs N-way
grouping rather than pairwise old-vs-new comparison. When a base record and a
non-base record share an identity, the base record always wins and its bytes
stay untouched; --on-conflict's keep-first/keep-last only disambiguates among
duplicates that are *not* shared with base. A metadata conflict (any
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
from .xmlio import ET, parse_xml_bytes
from .xmlio import ET

_TRACKED_ATTRS = ("artist", "title", "album", "filesize", "playtime_float", "bitrate")


@dataclass
class ConflictRow:
    identity_key: str
    attrs: str
    resolution: str


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


def _resolve_conflicts(
    groups: dict[int, list[tuple[int, EntryRecord]]],
    on_conflict: Optional[str],
    *,
    resolutions: Optional[dict[str, str]] = None,
) -> tuple[dict[str, str], list[ConflictRow], bool, list[tuple[int, EntryRecord]], set[str]]:
    """Return (old_to_new_key, conflict_rows, unresolved, new_entries,
    ambiguous_keys).

    resolutions maps an identity-group key to the token base or source and
    settles that one group; on_conflict settles every group the mapping does
    not name. It is a keyword parameter rather than an appended positional,
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
    """
    old_to_new_key: dict[str, str] = {}
    conflict_rows: list[ConflictRow] = []
    new_entries: list[tuple[int, EntryRecord]] = []
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
        # entry is inert rather than an error (DL-105).
        resolution = resolutions.get(identity_key) if divergent_attrs else None
        if divergent_attrs and resolution is None and on_conflict is None:
            unresolved = True
            conflict_rows.append(ConflictRow(identity_key, ",".join(divergent_attrs), "unresolved"))
            continue

        base_members = [(idx, r) for idx, r in members if idx == 0]
        if len(base_members) > 1:
            for idx, record in members:
                if idx != 0:
                    ambiguous_keys.add(record.primary_key)
        base_member = base_members[0] if base_members else None
        # source hands the group to the same run-wide picker that decides
        # among duplicates no base record shares, so one picker answers
        # "which non-base copy" wherever that question is asked.
        if resolution == "source" or base_member is None:
            candidates = [(idx, r) for idx, r in members if idx != 0] or members
            policy = on_conflict or "keep-first"
            picker = min if policy == "keep-first" else max
            winner_idx, winner = picker(candidates, key=lambda m: m[0])
            new_entries.append((winner_idx, winner))
        else:
            winner_idx, winner = base_member

        for _, record in members:
            if record is not winner:
                old_to_new_key[record.primary_key] = winner.primary_key

        if divergent_attrs:
            conflict_rows.append(
                ConflictRow(identity_key, ",".join(divergent_attrs), resolution or on_conflict)
            )

    return old_to_new_key, conflict_rows, unresolved, new_entries, ambiguous_keys


def _entry_span_text(source_text: str, span_index: SpanIndex, record: EntryRecord) -> str:
    return span_index.span_of(record.entry).text(source_text)


def assemble_output(
    base_source: str,
    base_root: ET.Element,
    contributions: list[tuple[str, ET.Element]],
    confidence: MatchConfidence,
    on_conflict: Optional[str] = None,
    reconstruct: bool = False,
    *,
    resolutions: Optional[dict[str, str]] = None,
) -> SpliceResult:
    """Merge every contribution into base_source: build cross-input
    identity groups, resolve conflicts (aborting with zero output on any
    unresolved one), transplant surviving collection entries as verbatim
    spans, then hand off to playlist import for the PLAYLISTS tree
    (DL-007, DL-008).

    resolutions maps an identity-group key to base or source and settles
    that group alone. An empty mapping leaves every group to on_conflict,
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
    old_to_new_key, conflict_rows, unresolved, new_entries_records, ambiguous_keys = _resolve_conflicts(
        groups, on_conflict, resolutions=resolutions
    )

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

        replacements: list[tuple[int, int, str]] = []
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

        for start_at, end_at, fragment in sorted(replacements, reverse=True):
            base_source = base_source[:start_at] + fragment + base_source[end_at:]
        if replacements:
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

    return SpliceResult(output=output, stats=stats, conflict_rows=conflict_rows, errors=[])
