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
differing attribute between two copies of one identity) aborts the whole
write unless --on-conflict is given, and the conflict report is written
either way (DL-008). Fragments no rename or redirect touched are transplanted
as source byte spans (spans.py); only renamed playlists and redirected
PRIMARYKEY values are re-serialised.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .confidence import MatchConfidence
from .matching import record_keys
from .model import EntryRecord, collection_entries, collection_records
from .playlists import find_playlist_nodes, import_playlists, node_primary_keys
from .spans import OutputBuilder, SpanIndex, find_element_span
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


def _resolve_conflicts(
    groups: dict[int, list[tuple[int, EntryRecord]]], on_conflict: Optional[str]
) -> tuple[dict[str, str], list[ConflictRow], bool, list[tuple[int, EntryRecord]]]:
    """Return (old_to_new_key, conflict_rows, unresolved, new_entries).

    new_entries lists (input_idx, record) for exactly the records that must
    be added to the merged COLLECTION: the sole record of a single-input
    group not owned by the base, or a cross-input group's non-base winner.
    input_idx disambiguates which source text to transplant the entry's
    span from, since two distinct records can carry identical field values.
    """
    old_to_new_key: dict[str, str] = {}
    conflict_rows: list[ConflictRow] = []
    new_entries: list[tuple[int, EntryRecord]] = []
    unresolved = False

    for key, members in groups.items():
        contributing_inputs = {idx for idx, _ in members}
        if len(contributing_inputs) == 1:
            idx = next(iter(contributing_inputs))
            if idx != 0:
                new_entries.append(members[0])
            continue

        divergent_attrs = [
            attr for attr in _TRACKED_ATTRS if len({getattr(r, attr) for _, r in members}) > 1
        ]
        if divergent_attrs and on_conflict is None:
            unresolved = True
            conflict_rows.append(ConflictRow(str(key), ",".join(divergent_attrs), "unresolved"))
            continue

        base_member = next(((idx, r) for idx, r in members if idx == 0), None)
        if base_member is not None:
            winner_idx, winner = base_member
        else:
            policy = on_conflict or "keep-first"
            picker = min if policy == "keep-first" else max
            winner_idx, winner = picker(members, key=lambda m: m[0])
            new_entries.append((winner_idx, winner))

        for _, record in members:
            if record is not winner:
                old_to_new_key[record.primary_key] = winner.primary_key

        if divergent_attrs:
            conflict_rows.append(ConflictRow(str(key), ",".join(divergent_attrs), on_conflict or "unresolved"))

    return old_to_new_key, conflict_rows, unresolved, new_entries


def _entry_span_text(source_text: str, span_index: SpanIndex, record: EntryRecord) -> str:
    return span_index.span_of(record.entry).text(source_text)


def assemble_output(
    base_source: str,
    base_root: ET.Element,
    contributions: list[tuple[str, ET.Element]],
    confidence: MatchConfidence,
    on_conflict: Optional[str] = None,
) -> SpliceResult:
    """Merge every contribution into base_source: build cross-input
    identity groups, resolve conflicts (aborting with zero output on any
    unresolved one), transplant surviving collection entries as verbatim
    spans, then hand off to playlist import for the PLAYLISTS tree
    (DL-007, DL-008)."""
    inputs = [base_root] + [root for _, root in contributions]
    sources = [base_source] + [text for text, _ in contributions]
    records_by_input = [collection_records(root) for root in inputs]

    # One SpanIndex per input source, built once here rather than once per
    # entry or per playlist, so a merge scans each source once regardless
    # of how many entries and playlists it contributes.
    span_indexes = [SpanIndex(sources[i], inputs[i]) for i in range(len(inputs))]

    groups = group_identities(records_by_input, confidence)
    old_to_new_key, conflict_rows, unresolved, new_entries_records = _resolve_conflicts(groups, on_conflict)

    stats = {
        "inputs_merged": len(contributions),
        "identity_groups": len(groups),
        "conflicts_reported": len(conflict_rows),
        "collection_entries_added": 0,
        "playlists_imported": 0,
        "playlists_renamed": 0,
        "sorting_info_dropped": [],
    }

    if unresolved:
        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=["unresolved_conflicts"])

    # New collection entries: transplant each winner's own ENTRY span from
    # its originating input, verbatim (collection entries are never renamed).
    new_entry_texts = [
        _entry_span_text(sources[idx], span_indexes[idx], record) for idx, record in new_entries_records
    ]
    stats["collection_entries_added"] = len(new_entry_texts)

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
    playlist_fragments: list[str] = []
    sorting_info_fragments: list[str] = []
    sorting_info_dropped: list[str] = []
    unresolved_refs: list[tuple[str, str]] = []
    renamed_count = 0
    for contribution_idx, (source_text, root) in enumerate(contributions, start=1):
        result = import_playlists(
            source_text, root, old_to_new_key, existing_names, span_indexes[contribution_idx]
        )
        for imported in result.playlists:
            playlist_fragments.append(imported.fragment)
        sorting_info_fragments.extend(result.sorting_info)
        sorting_info_dropped.extend(result.dropped_sorting_info)
        renamed_count += len(result.renamed)
    stats["playlists_imported"] = len(playlist_fragments)
    stats["playlists_renamed"] = renamed_count
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
