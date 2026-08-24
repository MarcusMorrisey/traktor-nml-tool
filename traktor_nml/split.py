"""Partition one NML into several outputs by named playlist, keeping every
kept fragment byte-identical to its source span.

Every output is a flat playlist-entry subset (v1 scope, see the plan's
tradeoffs): a --group names one or more playlists whose entries define that
output's COLLECTION. Dangling references - a kept playlist pointing at a
track outside the selection - are excluded by default, referentially closing
every output; pull-in and fail are explicit alternatives (DL-009).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from .model import collection_records
from .playlists import find_playlist_nodes, find_sorting_info, node_primary_keys, playlist_paths
from .spans import SpanIndex, find_element_span, recalculate_count_attr
from .xmlio import ET

DanglingPolicy = Literal["exclude", "pull-in", "fail"]


@dataclass
class SelectionResult:
    """playlist_partial's (name, kept, total) records the partial-
    retention detail DL-009 requires reporting, distinct from
    playlist_dropped's fully-empty case - a playlist never silently loses
    entries without one of the two being reported."""
    kept_keys: set[str]
    resolved_nodes: list[ET.Element] = field(default_factory=list)
    playlist_dropped: list[str] = field(default_factory=list)
    playlist_partial: list[tuple[str, int, int]] = field(default_factory=list)  # (name, kept, total)
    unknown_playlists: list[str] = field(default_factory=list)


def select_entries(root: ET.Element, playlist_names: list[str]) -> SelectionResult:
    """Resolve playlist_names to their primary keys, and report a playlist
    reduced to zero entries as dropped rather than writing it empty.
    resolved_nodes carries every playlist node this group actually
    resolved to, so apply_dangling_policy can scope its dangling-reference
    check to only these nodes rather than searching the document again."""
    all_nodes = {node.attrib.get("NAME", ""): node for node in find_playlist_nodes(root)}
    result = SelectionResult(kept_keys=set())

    for name in playlist_names:
        node = all_nodes.get(name)
        if node is None:
            result.unknown_playlists.append(name)
            continue
        result.resolved_nodes.append(node)
        keys = [pk.attrib.get("KEY", "") for pk in node_primary_keys(node)]
        total = len(keys)
        if total == 0:
            result.playlist_dropped.append(name)
            continue
        result.kept_keys.update(keys)

    return result


@dataclass
class SplitOutcome:
    output: Optional[str]
    stats: dict[str, object]
    errors: list[str] = field(default_factory=list)


def apply_dangling_policy(
    root: ET.Element, kept_keys: set[str], policy: DanglingPolicy, playlist_nodes: list[ET.Element]
) -> tuple[set[str], list[tuple[str, str]], list[str]]:
    """Return (final_kept_keys, dropped_refs, errors).

    exclude drops out-of-selection references (default, always closed).
    pull-in adds the referenced entries' keys into the selection instead.
    fail reports every offending reference as an error and adds nothing.
    """
    # exclude is split's default (DL-009): pull-in would duplicate a
    # track across outputs and reintroduce the divergence splice exists
    # to resolve; fail is available for callers that would rather refuse
    # outright than silently narrow a playlist.
    valid_collection_keys = {r.primary_key for r in collection_records(root)}
    dropped_refs: list[tuple[str, str]] = []
    errors: list[str] = []
    # A key select_entries gathered but that matches no actual COLLECTION
    # entry (an already-broken reference in the source) can never define a
    # kept track either, so it is excluded from the carried-over selection
    # up front and handled below like any other out-of-selection reference.
    final_keys = kept_keys & valid_collection_keys

    for node in playlist_nodes:
        name = node.attrib.get("NAME", "")
        for pk in node_primary_keys(node):
            key = pk.attrib.get("KEY", "")
            if key in final_keys:
                continue
            # key references something outside the current selection - either
            # elsewhere in this file's own COLLECTION, or nowhere at all (an
            # already-broken reference). Either way it is dangling relative
            # to this output and goes through the same policy.
            if policy == "pull-in" and key in valid_collection_keys:
                final_keys.add(key)
            elif policy == "fail":
                errors.append(f"dangling_reference playlist={name} key={key}")
            else:
                dropped_refs.append((name, key))

    return final_keys, dropped_refs, errors


def _replace_children(fragment: str, tag_name: str, count_attr: str, children: list[str]) -> str:
    """Rewrite fragment's own opening tag's count_attr to len(children) and
    replace everything between the opening and closing tag with children,
    discarding the original body entirely (a full-selection rebuild, unlike
    splice's append-only merge)."""
    fragment = recalculate_count_attr(fragment, tag_name, count_attr, len(children))
    open_end = fragment.index(">") + 1
    close_start = len(fragment) - len(f"</{tag_name}>")
    return fragment[:open_end] + "".join(children) + fragment[close_start:]


def build_output(
    source_text: str, root: ET.Element, playlist_names: list[str], policy: DanglingPolicy, span_index: SpanIndex
) -> SplitOutcome:
    selection = select_entries(root, playlist_names)
    stats: dict[str, object] = {
        "playlists_requested": len(playlist_names),
        "playlists_dropped": list(selection.playlist_dropped),
        "playlists_unknown": list(selection.unknown_playlists),
    }

    final_keys, dropped_refs, errors = apply_dangling_policy(
        root, selection.kept_keys, policy, selection.resolved_nodes
    )
    if errors:
        return SplitOutcome(output=None, stats=stats, errors=errors)

    kept_records = [r for r in collection_records(root) if r.primary_key in final_keys]
    try:
        # Each ENTRY's span is located by its own parsed element (identity),
        # not by searching source text for its FILE attribute value - that
        # search breaks on duplicate basenames (common across a real corpus)
        # and on XML-escaped characters, since the parsed attribute value is
        # unescaped text while the source bytes are not.
        kept_entry_texts = [span_index.span_of(r.entry).text(source_text) for r in kept_records]
    except ValueError as exc:
        return SplitOutcome(output=None, stats=stats, errors=[f"collection_entry_span_not_found: {exc}"])

    collection_span = find_element_span(source_text, "COLLECTION")
    if collection_span is None:
        return SplitOutcome(output=None, stats=stats, errors=["no_collection"])
    coll_fragment = _replace_children(
        collection_span.text(source_text), "COLLECTION", "ENTRIES", kept_entry_texts
    )
    output = source_text[: collection_span.start] + coll_fragment + source_text[collection_span.end:]

    # Rebuild the PLAYLISTS tree: keep only the requested, non-dropped
    # playlists, transplanted verbatim except for dropped references, which
    # are excluded (their ENTRY/PRIMARYKEY child text is simply omitted).
    requested_kept_names = [
        name for name in playlist_names
        if name not in selection.playlist_dropped and name not in selection.unknown_playlists
    ]
    dropped_keys_by_name: dict[str, set[str]] = {}
    for name, key in dropped_refs:
        dropped_keys_by_name.setdefault(name, set()).add(key)

    playlist_fragments = []
    retained_names: list[str] = []
    partial: list[tuple[str, int, int]] = []
    for node in find_playlist_nodes(root):
        name = node.attrib.get("NAME", "")
        if name not in requested_kept_names:
            continue
        all_keys = [pk.attrib.get("KEY", "") for pk in node_primary_keys(node)]
        excluded = dropped_keys_by_name.get(name, set())
        surviving = [k for k in all_keys if k not in excluded]
        if not surviving:
            stats.setdefault("playlists_dropped", []).append(name)  # type: ignore[union-attr]
            continue
        if excluded:
            partial.append((name, len(surviving), len(all_keys)))
            # Clone the real element and prune the dropped ENTRY children in
            # place, then re-serialise: this preserves every surviving
            # ENTRY/PRIMARYKEY's original attributes verbatim (in particular
            # PRIMARYKEY TYPE, which may be STEM rather than TRACK) and lets
            # the serialiser handle NAME/KEY escaping correctly, instead of
            # a hand-built f-string that hardcodes TYPE="TRACK" and
            # interpolates NAME/KEY unescaped.
            node_copy = ET.fromstring(ET.tostring(node))
            playlist_elem = node_copy.find("PLAYLIST")
            if playlist_elem is not None:
                for entry_elem in list(playlist_elem.findall("ENTRY")):
                    pk_elem = entry_elem.find("PRIMARYKEY")
                    entry_key = "" if pk_elem is None else pk_elem.attrib.get("KEY", "")
                    if entry_key in excluded:
                        playlist_elem.remove(entry_elem)
                playlist_elem.attrib["ENTRIES"] = str(len(surviving))
            fragment = ET.tostring(node_copy, encoding="unicode")
        else:
            try:
                fragment = span_index.span_of(node).text(source_text)
            except ValueError as exc:
                return SplitOutcome(output=None, stats=stats, errors=[f"playlist_span_not_found name={name}: {exc}"])
        playlist_fragments.append(fragment)
        retained_names.append(name)
    stats["playlists_partial"] = partial

    subnodes_span = find_element_span(output, "SUBNODES")
    if subnodes_span is None:
        return SplitOutcome(output=None, stats=stats, errors=["no_root_subnodes"])
    subnodes_fragment = _replace_children(
        subnodes_span.text(output), "SUBNODES", "COUNT", playlist_fragments
    )
    output = output[: subnodes_span.start] + subnodes_fragment + output[subnodes_span.end:]

    # A playlist this output does not retain - never requested, unknown,
    # or emptied entirely by the dangling policy - leaves its matching
    # SORTING_INFO entry (if the source has one) referencing a playlist
    # that no longer exists in this output. That entry is dropped from the
    # output's INDEXING section here, and reported, rather than left
    # orphaned (DL-009).
    nodes_by_name = {node.attrib.get("NAME", ""): node for node in find_playlist_nodes(root)}
    dropped_names = set(nodes_by_name) - set(retained_names)
    node_paths = {id(node): path for path, node in playlist_paths(root).items()}
    dropped_paths = {
        node_paths[id(nodes_by_name[name])]
        for name in dropped_names
        if name in nodes_by_name and id(nodes_by_name[name]) in node_paths
    }
    removed_sorting_info = [si for si in find_sorting_info(root) if si.attrib.get("PATH", "") in dropped_paths]
    stats["sorting_info_dropped"] = [si.attrib.get("PATH", "") for si in removed_sorting_info]

    indexing_span = find_element_span(output, "INDEXING")
    if indexing_span is not None and removed_sorting_info:
        removed_ids = {id(si) for si in removed_sorting_info}
        kept_sorting_info = [
            span_index.span_of(si).text(source_text)
            for si in find_sorting_info(root)
            if id(si) not in removed_ids
        ]
        indexing_fragment = _replace_children(
            indexing_span.text(output), "INDEXING", "COUNT", kept_sorting_info
        )
        output = output[: indexing_span.start] + indexing_fragment + output[indexing_span.end:]

    stats["kept_entries"] = len(kept_entry_texts)
    return SplitOutcome(output=output, stats=stats, errors=[])
