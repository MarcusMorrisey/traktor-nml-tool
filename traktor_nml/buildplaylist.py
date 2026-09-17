"""build-playlist core: resolution, playlist synthesis, insertion.

A build-playlist run takes the ordered Candidate list
playlistinput.read_input produced (DL-274, DL-281), resolves each
candidate against a base collection through tracklist.resolve_candidates
at MatchConfidence.LOOSE, synthesizes a NODE TYPE=PLAYLIST fragment from the
resolved primary keys in input order (playlists.synthesize_playlist_node),
and inserts it into the base's root FOLDER SUBNODES, or a named existing
folder's SUBNODES, through the same byte-span assembly spans.py's other
structural commands (splice.py/split.py) already use. No source span
exists for a playlist assembled from external text, so its fragment
always takes the ElementTree-serialization path (DL-028) rather than
transplantation. matching.py and confidence.py are reached only through
tracklist.py's own calls and are never edited here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .model import collection_records
from .playlists import available_playlist_name, find_playlist_nodes, synthesize_playlist_node
from .spans import OutputBuilder, SpanIndex, find_element_span
from .tracklist import Candidate, resolve_candidates


@dataclass
class UnresolvedRow:
    """One input entry that did not become a written ENTRY, and why.
    line_number and raw_text carry the meaning given by the
    playlistinput.py reader that produced the candidate (read_csv,
    read_m3u, read_folder; read_text's candidates come from
    tracklist.text_candidates, which states it)."""
    line_number: int
    raw_text: str
    artist: str
    title: str
    kind: str  # "unparseable", "unmatched", "ambiguous"


@dataclass
class BuildPlaylistResult:
    """output is None exactly when errors is non-empty. unresolved_rows is
    populated on every run, including a clean one, so the report is a
    record of what the run saw rather than only of what failed (DL-027,
    DL-034)."""
    output: Optional[str]
    stats: dict[str, object]
    unresolved_rows: list[UnresolvedRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _find_target_subnodes(base_root, base_source: str, target_folder: Optional[str]):
    """Return (subnodes_span, existing_child_count, error) for the
    receiving SUBNODES: the default root folder's SUBNODES (the first
    SUBNODES span in the document, matching splice.py's own default), or
    the SUBNODES of the FOLDER named target_folder, resolved against the
    parsed tree and a SpanIndex rather than by document position, so a
    name collision across folders is never resolved by picking the first
    match (DL-030). The named-folder search is scoped to descendants of
    the PLAYLISTS root NODE, matching DL-030's own wording ('anywhere in
    the PLAYLISTS tree') - a same-named FOLDER living outside PLAYLISTS
    (there is none in the confirmed schema, but nothing rules one out)
    must never satisfy or falsely ambiguate this lookup. target_folder
    naming the root NODE's own NAME (conventionally "$ROOT") takes the
    default-root path rather than the descendant search, so it behaves
    the same as omitting --target-folder. A base with no PLAYLISTS
    section, root FOLDER, or SUBNODES element at all reports
    no_root_subnodes, mirroring splice.py's own check for the identical
    absence (DL-038); a root SUBNODES element that exists in the parsed
    tree but whose span cannot be located in the raw source text reports
    the distinct root_subnodes_span_not_found; a named folder that exists
    but has no SUBNODES child of its own reports the distinct
    target_folder_no_subnodes."""
    playlists_root = base_root.find(".//PLAYLISTS/NODE")
    if playlists_root is None or playlists_root.find("SUBNODES") is None:
        return None, 0, "no_root_subnodes"

    # target_folder naming the root NODE's own NAME (conventionally "$ROOT")
    # takes the same default-root path as omitting --target-folder: the
    # descendant-only findall() below would otherwise never match the root
    # NODE itself and wrongly report target_folder_not_found.
    if target_folder is None or playlists_root.attrib.get("NAME", "") == target_folder:
        subnodes_span = find_element_span(base_source, "SUBNODES")
        if subnodes_span is None:
            # distinct from the whole-document no_root_subnodes case above:
            # the root SUBNODES element does exist in the parsed tree (the
            # check above already confirmed it), but its span could not be
            # located in the raw source text - a source/tree mismatch, not
            # an absence of subnodes
            return None, 0, "root_subnodes_span_not_found"
        root_subnodes_elem = playlists_root.find("SUBNODES")
        count = 0 if root_subnodes_elem is None else len(list(root_subnodes_elem))
        return subnodes_span, count, None

    matching_folders = [
        folder for folder in playlists_root.findall(".//NODE[@TYPE='FOLDER']")
        if folder.attrib.get("NAME", "") == target_folder
    ]
    if not matching_folders:
        return None, 0, "target_folder_not_found"
    if len(matching_folders) > 1:
        return None, 0, f"target_folder_ambiguous={target_folder}:count={len(matching_folders)}"

    folder_subnodes = matching_folders[0].find("SUBNODES")
    if folder_subnodes is None:
        # distinct from the whole-document no_root_subnodes case above: the
        # named folder itself exists but is malformed, not absent
        return None, 0, "target_folder_no_subnodes"

    span_index = SpanIndex(base_source, base_root)
    subnodes_span = span_index.span_of(folder_subnodes)
    count = len(list(folder_subnodes))
    return subnodes_span, count, None


def _resolve_lines(candidates: list[Candidate], records):
    """Resolve every candidate against records and split the results into
    matched primary keys, unresolved rows sorted by line_number, and the
    run's stats dict. The stats keys and their order are fixed (DL-280):
    the CLI prints them as they stand, and the text corpus replays that
    output byte for byte (DL-279)."""
    resolutions = resolve_candidates(candidates, records)

    unresolved_rows: list[UnresolvedRow] = []
    matched_keys: list[str] = []
    for resolution in resolutions:
        if resolution.outcome == "matched":
            matched_keys.append(resolution.matched_record.primary_key)
        else:
            candidate = resolution.candidate
            unresolved_rows.append(
                UnresolvedRow(
                    line_number=candidate.line_number, raw_text=candidate.raw_text,
                    artist=candidate.artist, title=candidate.title, kind=resolution.outcome,
                )
            )
    # Stable sort: candidates already arrive in line order, so this
    # reorders nothing and ties keep their input order.
    unresolved_rows.sort(key=lambda row: row.line_number)

    def _count(outcome: str) -> int:
        return sum(1 for r in resolutions if r.outcome == outcome)

    stats: dict[str, object] = {
        "lines_read": len(candidates),
        "lines_resolved": len(matched_keys),
        "unresolved_unparseable": _count("unparseable"),
        "unresolved_unmatched": _count("unmatched"),
        "unresolved_ambiguous": _count("ambiguous"),
        "playlist_name": None,
        "entries_written": 0,
    }
    return matched_keys, unresolved_rows, stats


def assemble_output(
    base_source: str,
    base_root,
    candidates: list[Candidate],
    playlist_name: str,
    target_folder: Optional[str] = None,
    allow_unmatched: bool = False,
) -> BuildPlaylistResult:
    """Resolve every candidate against the base collection, synthesize
    a playlist from the resolved primary keys in input order, and splice
    it into the receiving SUBNODES. Returns output None with
    unresolved_tracks when any candidate is unresolved and allow_unmatched is
    false (DL-027); output None with no_entries_resolved, before any span
    lookup, when zero candidates resolve, including an input that yielded
    no candidates at all (DL-036); output None with
    no_root_subnodes/root_subnodes_span_not_found/target_folder_not_found/
    target_folder_no_subnodes/target_folder_ambiguous=name:count=N when the
    receiving container cannot be resolved (DL-030, DL-038). Duplicate
    candidates naming the same track resolve and serialize
    independently (DL-037). Every synthesized key is validated against the
    base collection's own primary keys before returning, mirroring
    splice.py's validate-before-write convention. The whole output is built
    and validated in memory before the caller opens any file handle."""
    records = collection_records(base_root)
    # candidates arrive already read and ordered by playlistinput.read_input
    # (DL-281); resolution, refusal and the report see one shape (DL-274).
    matched_keys, unresolved_rows, stats = _resolve_lines(candidates, records)

    if unresolved_rows and not allow_unmatched:
        return BuildPlaylistResult(output=None, stats=stats, unresolved_rows=unresolved_rows, errors=["unresolved_tracks"])

    if not matched_keys:
        return BuildPlaylistResult(output=None, stats=stats, unresolved_rows=unresolved_rows, errors=["no_entries_resolved"])

    subnodes_span, existing_count, error = _find_target_subnodes(base_root, base_source, target_folder)
    if error is not None:
        return BuildPlaylistResult(output=None, stats=stats, unresolved_rows=unresolved_rows, errors=[error])

    # Every matched_keys entry comes from resolution.matched_record, which
    # resolve_candidates draws only from this same records list, so this can
    # never actually fail - checked anyway to match splice.py's own
    # validate-before-write convention for playlist PRIMARYKEY references.
    valid_keys = {r.primary_key for r in records}
    invalid_keys = [key for key in matched_keys if key not in valid_keys]
    if invalid_keys:
        errors = [f"unresolved_reference key={key}" for key in invalid_keys]
        return BuildPlaylistResult(output=None, stats=stats, unresolved_rows=unresolved_rows, errors=errors)

    existing_names = {node.attrib.get("NAME", "") for node in find_playlist_nodes(base_root)}
    final_name = available_playlist_name(playlist_name, existing_names)
    fragment = synthesize_playlist_node(final_name, matched_keys)
    stats["playlist_name"] = final_name
    stats["entries_written"] = len(matched_keys)

    builder = OutputBuilder()
    builder.add_verbatim(base_source[: subnodes_span.start])
    # existing_count + 1: the synthesized PLAYLIST node is the one new
    # child being added to the receiving SUBNODES element.
    builder.add_counted_span(
        base_source, subnodes_span, "SUBNODES", "COUNT", [fragment],
        count=existing_count + 1,
    )
    builder.add_verbatim(base_source[subnodes_span.end:])
    output = builder.build()

    return BuildPlaylistResult(output=output, stats=stats, unresolved_rows=unresolved_rows, errors=[])
