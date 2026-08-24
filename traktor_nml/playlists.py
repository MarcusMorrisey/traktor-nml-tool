"""Playlist import for splice: every non-base playlist becomes a base child.

Every NODE TYPE=PLAYLIST anywhere in a non-base input's PLAYLISTS tree
qualifies for import, no folder-location filtering - imported playlists are
flattened one level as new children of the base root FOLDER's SUBNODES
(folder nesting beyond a playlist's own node is out of scope for v1, see the
plan's tradeoffs). PRIMARYKEY entries are retained verbatim unless their
referenced track lost an identity conflict, in which case they redirect to
the winner's key. A same-name collision gets a deterministic "<name> (2)"
rename with a freshly generated UUID - never the source UUID, which would
create a duplicate within the output file.

Traktor's tolerance of that fresh UUID on a renamed/imported playlist is
confirmed only by manual Traktor import/open validation, not by this test
suite (DL-008); the regenerated UUID is an accepted, unverified risk
until that manual check is repeated for a given output.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from .spans import SpanIndex
from .xmlio import ET


@dataclass
class ImportedPlaylist:
    """is_verbatim=False marks a fragment that was re-serialised because
    at least one of its PRIMARYKEY values was redirected or its NAME was
    renamed for a collision; the source span is otherwise copied
    unchanged."""
    fragment: str  # verbatim span text or a re-serialised replacement
    is_verbatim: bool
    original_name: str
    final_name: str


@dataclass
class ImportResult:
    playlists: list[ImportedPlaylist] = field(default_factory=list)
    renamed: dict[str, str] = field(default_factory=dict)  # original_name -> final_name
    sorting_info: list[str] = field(default_factory=list)  # rewritten SORTING_INFO fragments to carry over
    dropped_sorting_info: list[str] = field(default_factory=list)  # PATHs that could not be carried over


def find_playlist_nodes(root: ET.Element) -> list[ET.Element]:
    return root.findall(".//NODE[@TYPE='PLAYLIST']")


def node_primary_keys(node: ET.Element) -> list[ET.Element]:
    playlist = node.find("PLAYLIST")
    return [] if playlist is None else playlist.findall(".//PRIMARYKEY")


def find_sorting_info(root: ET.Element) -> list[ET.Element]:
    """Every SORTING_INFO entry under INDEXING, in document order."""
    return root.findall(".//INDEXING/SORTING_INFO")


def playlist_paths(root: ET.Element) -> dict[str, ET.Element]:
    """Map each playlist NODE to the backslash-joined folder path that
    SORTING_INFO's own PATH attribute uses to name it - ancestor FOLDER
    names down to (and including) the playlist's own NAME, with the tree's
    own root FOLDER (conventionally $ROOT) excluded, matching the encoding
    confirmed against the real fixture corpus. lxml elements carry no
    parent pointers of their own, so this is computed top-down by walking
    the PLAYLISTS tree rather than read off each NODE directly."""
    result: dict[str, ET.Element] = {}
    playlists_root = root.find(".//PLAYLISTS/NODE")
    if playlists_root is None:
        return result

    def walk(node: ET.Element, prefix: list[str]) -> None:
        node_type = node.attrib.get("TYPE")
        name = node.attrib.get("NAME", "")
        if node_type == "PLAYLIST":
            result["\\".join(prefix + [name])] = node
        elif node_type == "FOLDER":
            subnodes = node.find("SUBNODES")
            if subnodes is not None:
                for child in subnodes:
                    walk(child, prefix + [name])

    root_subnodes = playlists_root.find("SUBNODES")
    if root_subnodes is not None:
        for child in root_subnodes:
            walk(child, [])

    return result


def _sorting_info_fragment(sorting_info: ET.Element, new_path: str) -> str:
    """Re-serialise a SORTING_INFO element with PATH rewritten to
    new_path, keeping every child CRITERIA element untouched."""
    node_copy = ET.fromstring(ET.tostring(sorting_info))
    node_copy.attrib["PATH"] = new_path
    return ET.tostring(node_copy, encoding="unicode")


def _redirect_keys(node_copy: ET.Element, old_to_new_key: dict[str, str]) -> None:
    """Redirect PRIMARYKEY/KEY values on an in-memory copy in place."""
    for pk in node_primary_keys(node_copy):
        old_key = pk.attrib.get("KEY", "")
        new_key = old_to_new_key.get(old_key)
        if new_key is not None and new_key != old_key:
            pk.attrib["KEY"] = new_key


def available_playlist_name(requested_name: str, existing_names: set[str]) -> str:
    """Take a requested name and the set of names already in use and return
    the requested name when free, otherwise the first free numbered-suffix
    variant starting at 2, adding the result to the in-use set.
    import_playlists' own collision handling reads through this one
    function so the suffix rule has a single spelling shared by imported
    and synthesized playlists."""
    final_name = requested_name
    suffix = 2
    # starts at 2 so the first collision becomes "<name> (2)", the same
    # numbering import_playlists also uses (DL-029)
    while final_name in existing_names:
        final_name = f"{requested_name} ({suffix})"
        suffix += 1
    existing_names.add(final_name)
    return final_name


def import_playlists(
    source_text: str,
    non_base_root: ET.Element,
    old_to_new_key: dict[str, str],
    existing_names: set[str],
    span_index: SpanIndex,
) -> ImportResult:
    """Import every playlist NODE in non_base_root's tree, sourced from
    source_text for verbatim span transplantation.

    Each imported playlist's matching SORTING_INFO entry (found by its
    original folder path, if the source has one) is carried over with its
    PATH rewritten to the playlist's new flattened location (its final,
    possibly renamed, NAME); a SORTING_INFO entry with no matching playlist
    at all is dropped and reported rather than silently kept or fabricated.

    A node is located by its tree identity through span_index rather than
    by a document-wide UUID text search, so a PLAYLIST child with no UUID
    attribute is no longer a failure.
    """
    result = ImportResult()
    node_to_path = {id(node): path for path, node in playlist_paths(non_base_root).items()}
    sorting_info_by_path = {si.attrib.get("PATH", ""): si for si in find_sorting_info(non_base_root)}

    for path, sorting_info in sorting_info_by_path.items():
        if path.startswith("$"):
            continue  # system entries ($COLLECTION, $HASH, ...) are not playlist-specific
        if path not in node_to_path.values():
            result.dropped_sorting_info.append(path)

    for node in find_playlist_nodes(non_base_root):
        original_name = node.attrib.get("NAME", "")
        final_name = available_playlist_name(original_name, existing_names)
        renamed = final_name != original_name

        needs_redirect = any(
            old_to_new_key.get(pk.attrib.get("KEY", "")) not in (None, pk.attrib.get("KEY", ""))
            for pk in node_primary_keys(node)
        )

        if not renamed and not needs_redirect:
            span = span_index.span_of(node)
            fragment = span.text(source_text)
            is_verbatim = True
        else:
            node_copy = ET.fromstring(ET.tostring(node))
            if renamed:
                node_copy.attrib["NAME"] = final_name
                playlist_elem = node_copy.find("PLAYLIST")
                if playlist_elem is not None:
                    # A fresh UUID avoids duplicating the source playlist's
                    # UUID within this output file (two PLAYLIST nodes must
                    # not share one UUID). Traktor's tolerance of an
                    # imported playlist carrying a UUID other than the one
                    # it shipped with is confirmed only by manual Traktor
                    # import, not by this test suite.
                    playlist_elem.attrib["UUID"] = uuid.uuid4().hex
            _redirect_keys(node_copy, old_to_new_key)
            fragment = ET.tostring(node_copy, encoding="unicode")
            is_verbatim = False

        if renamed:
            result.renamed[original_name] = final_name

        result.playlists.append(
            ImportedPlaylist(
                fragment=fragment, is_verbatim=is_verbatim,
                original_name=original_name, final_name=final_name,
            )
        )

        original_path = node_to_path.get(id(node))
        sorting_info = sorting_info_by_path.get(original_path) if original_path is not None else None
        if sorting_info is not None:
            result.sorting_info.append(_sorting_info_fragment(sorting_info, final_name))

    return result


def synthesize_playlist_node(name: str, primary_keys: list[str]) -> str:
    """Take a playlist name and an ordered list of primary keys and return
    the serialized NODE TYPE=PLAYLIST fragment for them: a NODE carrying
    TYPE=PLAYLIST and NAME, holding one PLAYLIST child with TYPE=LIST,
    ENTRIES set to the key count, and UUID set to a fresh uuid4 hex,
    holding one ENTRY per key in the given order, each with a single
    PRIMARYKEY carrying TYPE=TRACK and KEY. The subtree is assembled as
    ElementTree elements and returned as ET.tostring output, so the name
    and every key are escaped by the serializer. It sits beside
    import_playlists because both emit a playlist fragment under the same
    naming and UUID policy, differing only in whether a source node
    exists."""
    node = ET.Element("NODE", {"TYPE": "PLAYLIST", "NAME": name})
    playlist_elem = ET.SubElement(
        node, "PLAYLIST",
        {"ENTRIES": str(len(primary_keys)), "TYPE": "LIST", "UUID": uuid.uuid4().hex},
    )
    for key in primary_keys:
        entry_elem = ET.SubElement(playlist_elem, "ENTRY")
        ET.SubElement(entry_elem, "PRIMARYKEY", {"TYPE": "TRACK", "KEY": key})
    # encoding="unicode" returns str (not bytes): callers splice this
    # fragment directly into a text-based document assembly (DL-028)
    return ET.tostring(node, encoding="unicode")
