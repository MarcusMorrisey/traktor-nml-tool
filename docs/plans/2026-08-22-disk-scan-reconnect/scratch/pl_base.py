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
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from .spans import Span, element_span
from .xmlio import ET


@dataclass
class ImportedPlaylist:
    fragment: str  # verbatim span text or a re-serialised replacement
    is_verbatim: bool
    original_name: str
    final_name: str
    unresolved_keys: list[str] = field(default_factory=list)


@dataclass
class ImportResult:
    playlists: list[ImportedPlaylist] = field(default_factory=list)
    renamed: dict[str, str] = field(default_factory=dict)  # original_name -> final_name
    dropped_sorting_info: list[str] = field(default_factory=list)
    unresolved_references: list[tuple[str, str]] = field(default_factory=list)  # (playlist_name, key)


def find_playlist_nodes(root: ET.Element) -> list[ET.Element]:
    return root.findall(".//NODE[@TYPE='PLAYLIST']")


def node_primary_keys(node: ET.Element) -> list[ET.Element]:
    playlist = node.find("PLAYLIST")
    return [] if playlist is None else playlist.findall(".//PRIMARYKEY")


def _redirect_keys(node_copy: ET.Element, old_to_new_key: dict[str, str]) -> tuple[bool, list[str]]:
    """Redirect PRIMARYKEY/KEY values on an in-memory copy; return whether
    anything changed and which keys could not be resolved at all (handled
    by the caller against the merged collection, not here)."""
    changed = False
    for pk in node_primary_keys(node_copy):
        old_key = pk.attrib.get("KEY", "")
        new_key = old_to_new_key.get(old_key)
        if new_key is not None and new_key != old_key:
            pk.attrib["KEY"] = new_key
            changed = True
    return changed, []


def import_playlists(
    source_text: str,
    non_base_root: ET.Element,
    old_to_new_key: dict[str, str],
    existing_names: set[str],
) -> ImportResult:
    """Import every playlist NODE in non_base_root's tree, sourced from
    source_text for verbatim span transplantation."""
    result = ImportResult()

    for node in find_playlist_nodes(non_base_root):
        original_name = node.attrib.get("NAME", "")
        final_name = original_name
        suffix = 2
        while final_name in existing_names:
            final_name = f"{original_name} ({suffix})"
            suffix += 1
        existing_names.add(final_name)
        renamed = final_name != original_name

        needs_redirect = any(
            old_to_new_key.get(pk.attrib.get("KEY", "")) not in (None, pk.attrib.get("KEY", ""))
            for pk in node_primary_keys(node)
        )

        if not renamed and not needs_redirect:
            node_start = _locate_node_start(source_text, node)
            span = element_span(source_text, node_start)
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
                    # import, not by this test suite (R-004).
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

    return result


def _locate_node_start(source_text: str, node: ET.Element) -> int:
    """Locate a playlist NODE's opening-tag offset via its PLAYLIST child's
    UUID, which is unique across the document (unlike NAME, which two
    playlists in different folders may share) - lxml elements carry no
    byte offsets of their own."""
    playlist_elem = node.find("PLAYLIST")
    uuid_value = "" if playlist_elem is None else playlist_elem.attrib.get("UUID", "")
    marker = f'UUID="{uuid_value}"'
    uuid_idx = source_text.find(marker)
    if uuid_idx < 0:
        raise ValueError(f"could not locate playlist UUID {uuid_value!r} in source text")
    node_idx = source_text.rfind("<NODE ", 0, uuid_idx)
    if node_idx < 0:
        raise ValueError(f"could not locate enclosing NODE for playlist UUID {uuid_value!r}")
    return node_idx
