"""playlists.playlist_folder_choices: the FOLDER nodes the build-playlist
screen's playlist-folder chooser lists (DL-297). System interpreter."""

from __future__ import annotations

from traktor_nml.playlists import PlaylistFolderChoice, playlist_folder_choices
from traktor_nml.xmlio import parse_xml_bytes


def _root(playlists: str):
    return parse_xml_bytes((
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        '<COLLECTION ENTRIES="0"></COLLECTION>'
        f"{playlists}<SETS></SETS><INDEXING></INDEXING></NML>"
    ).encode("utf-8"))


def _folder(name: str, inner: str = "") -> str:
    return f'<NODE TYPE="FOLDER" NAME="{name}"><SUBNODES COUNT="0">{inner}</SUBNODES></NODE>'


def _playlist(name: str) -> str:
    return f'<NODE TYPE="PLAYLIST" NAME="{name}"><PLAYLIST ENTRIES="0" TYPE="LIST" UUID="u"></PLAYLIST></NODE>'


def _tree(inner: str) -> str:
    return f'<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0">{inner}</SUBNODES></NODE></PLAYLISTS>'


def test_nested_paths_in_tree_order_root_and_playlists_excluded() -> None:
    """Folders come back parent before child in document order, paths
    joined with backslashes below $ROOT, no playlist and no root.

    Mutation: walk joins prefix + [name] with '/' in place of a
        backslash, so the nested folder's path reads 'Sets/2026'.
    Observed:
        E       AssertionError: assert [PlaylistFold... unique=True)] == [PlaylistFold... unique=True)]
        E
        E         At index 1 diff: PlaylistFolderChoice(path='Sets/2026', name='2026', unique=True) != PlaylistFolderChoice(path='Sets\\2026', name='2026', unique=True)
        E         Use -v to get more diff
    """
    root = _root(_tree(
        _folder("Sets", _folder("2026", _playlist("Aug")) + _playlist("Loose"))
        + _playlist("Top")
        + _folder("Archive")
    ))
    assert playlist_folder_choices(root) == [
        PlaylistFolderChoice("Sets", "Sets", True),
        PlaylistFolderChoice("Sets\\2026", "2026", True),
        PlaylistFolderChoice("Archive", "Archive", True),
    ]


def test_duplicate_name_flags_both_folders() -> None:
    """Two FOLDERs named 'Warmup' under different parents are both
    non-unique; their parents stay unique.

    Mutation: playlist_folder_choices passes True for unique on every
        choice, so both 'Warmup' folders read unique.
    Observed:
        E       assert [True, True, True, True] == [True, False, True, False]
        E
        E         At index 1 diff: True != False
        E         Use -v to get more diff
    """
    root = _root(_tree(_folder("Sets", _folder("Warmup")) + _folder("Archive", _folder("Warmup"))))
    choices = playlist_folder_choices(root)
    assert [c.path for c in choices] == ["Sets", "Sets\\Warmup", "Archive", "Archive\\Warmup"]
    assert [c.unique for c in choices] == [True, False, True, False]


def test_two_top_level_folders_named_sets_are_both_non_unique() -> None:
    """The acceptance case: a base with two FOLDERs named 'Sets' offers
    neither, since target_folder resolves by NAME alone (DL-297).

    Mutation: playlist_folder_choices marks a choice unique when its
        name has not appeared earlier in the walk, so the first 'Sets'
        reads unique.
    Observed:
        E       assert [True, False] == [False, False]
        E
        E         At index 0 diff: True != False
        E         Use -v to get more diff
    """
    root = _root(_tree(_folder("Sets") + _folder("Sets")))
    assert [c.unique for c in playlist_folder_choices(root)] == [False, False]


def test_missing_playlists_or_subnodes_gives_empty_list() -> None:
    """An NML with no PLAYLISTS root, or a root without SUBNODES, gives
    an empty list rather than an error.

    Mutation: playlist_folder_choices drops its
        `playlists_root.find('SUBNODES') is None` check, so the root
        without SUBNODES raises TypeError when its missing SUBNODES is
        iterated.
    Observed:
        E       TypeError: 'NoneType' object is not iterable
    """
    assert playlist_folder_choices(_root("")) == []
    assert playlist_folder_choices(_root('<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"></NODE></PLAYLISTS>')) == []
