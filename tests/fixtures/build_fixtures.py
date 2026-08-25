"""Deterministic synthetic NML fixture corpus.

Emits small hand-written NML files plus the audio stubs they reference,
covering the shapes the parity oracle and later milestones need: moved
paths, renamed files, two rips of one track at different bitrates, STEM
entries, ampersand and non-ASCII text, a nested playlist folder tree, an
empty playlist, SORTING_INFO entries, and a SETS section. Every fixture is
built from a fixed literal string, so regeneration is byte-identical.
"""

from __future__ import annotations

from pathlib import Path

_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'


def _entry(artist, title, volume, dirv, filename, size="4096", time="180.0", bitrate="320", album=None, audio_id="", extra_attrs=""):
    """Render one COLLECTION ENTRY as a literal string so every fixture
    byte is fixed at authoring time and regeneration is byte-identical."""
    album_elem = f'<ALBUM TITLE="{album}"></ALBUM>' if album else ""
    return (
        f'<ENTRY MODIFIED_DATE="2024/1/1" MODIFIED_TIME="0" AUDIO_ID="{audio_id}" '
        f'TITLE="{title}" ARTIST="{artist}"{extra_attrs}>'
        f"{album_elem}"
        f'<LOCATION DIR="{dirv}" FILE="{filename}" VOLUME="{volume}" VOLUMEID="{volume}"></LOCATION>'
        f'<INFO BITRATE="{bitrate}" PLAYTIME="180" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
        f"</ENTRY>\n"
    )


def _primarykey_entry(entry_type, volume, dirv, filename):
    """Render a playlist ENTRY/PRIMARYKEY pair whose KEY is the flattened
    VOLUME+DIR+FILE concatenation every PRIMARYKEY in this schema uses."""
    key = f"{volume}{dirv}{filename}"
    return f'<ENTRY><PRIMARYKEY TYPE="{entry_type}" KEY="{key}"></PRIMARYKEY></ENTRY>\n'


FIXTURE_MOVED_PATHS = "moved_paths.nml"
FIXTURE_RENAMED_FILE = "renamed_file.nml"
FIXTURE_DUPLICATE_RIPS = "duplicate_rips.nml"
FIXTURE_STEMS_AND_TEXT = "stems_and_text.nml"
FIXTURE_PLAYLIST_TREE = "playlist_tree.nml"
FIXTURE_SETS_SECTION = "sets_section.nml"

ALL_FIXTURES = (
    FIXTURE_MOVED_PATHS,
    FIXTURE_RENAMED_FILE,
    FIXTURE_DUPLICATE_RIPS,
    FIXTURE_STEMS_AND_TEXT,
    FIXTURE_PLAYLIST_TREE,
    FIXTURE_SETS_SECTION,
)


def _wrap(collection_entries: str, playlists: str = "", sorting_info: str = "", sets: str = "") -> str:
    return (
        _HEAD
        + '<NML VERSION="20">'
        + '<HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        + f'<COLLECTION ENTRIES="{collection_entries.count("<ENTRY")}">'
        + collection_entries
        + "</COLLECTION>"
        + (playlists or '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS>')
        + f"<SETS>{sets}</SETS>"
        + f"<INDEXING>{sorting_info}</INDEXING>"
        + "</NML>"
    )


def _moved_paths() -> str:
    entries = _entry("Aphex Twin", "Xtal", "C:", "/:Users/:dj/:Music/:", "xtal.mp3")
    return _wrap(entries)


def _renamed_file() -> str:
    entries = _entry("Boards of Canada", "Roygbiv", "C:", "/:Music/:", "roygbiv_final.mp3")
    return _wrap(entries)


def _duplicate_rips() -> str:
    entries = _entry(
        "Burial", "Archangel", "C:", "/:Music/:v1/:", "archangel_128.mp3", bitrate="128"
    ) + _entry(
        "Burial", "Archangel", "C:", "/:Music/:v2/:", "archangel_320.mp3", bitrate="320"
    )
    return _wrap(entries)


def _stems_and_text() -> str:
    # XML only defines &lt; &gt; &amp; &apos; &quot; as built-in entities - an
    # HTML named entity like &eacute; is undeclared and invalid here. The
    # accented character is written directly as a literal UTF-8 codepoint
    # (the document declares encoding="UTF-8"), and the literal ampersand is
    # escaped via the one XML entity that does cover it.
    entries = _entry(
        "Amélie &amp; Friends", "Café du Monde", "C:", "/:Music/:", "cafe.mp3", audio_id="STEMHOST1"
    ) + _primarykey_entry("STEM", "C:", "/:Music/:", "cafe.stem.mp3")
    return _wrap(entries)


def _playlist_tree() -> str:
    entry = _entry("Four Tet", "Baby", "C:", "/:Music/:", "baby.mp3")
    key = "C:" + "/:Music/:" + "baby.mp3"
    inner = (
        f'<PLAYLIST ENTRIES="1" TYPE="LIST" UUID="uuid-leaf"><ENTRY><PRIMARYKEY TYPE="TRACK" KEY="{key}"></PRIMARYKEY></ENTRY></PLAYLIST>'
    )
    empty_playlist = '<PLAYLIST ENTRIES="0" TYPE="LIST" UUID="uuid-empty"></PLAYLIST>'
    playlists = (
        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="2">'
        f'<NODE TYPE="FOLDER" NAME="Genres"><SUBNODES COUNT="1">'
        f'<NODE TYPE="FOLDER" NAME="Electronic"><SUBNODES COUNT="1">'
        f'<NODE TYPE="PLAYLIST" NAME="Leaf">{inner}</NODE>'
        "</SUBNODES></NODE>"
        "</SUBNODES></NODE>"
        f'<NODE TYPE="PLAYLIST" NAME="Empty">{empty_playlist}</NODE>'
        "</SUBNODES></NODE></PLAYLISTS>"
    )
    sorting_info = '<SORTING_INFO PATH="Genres\\Electronic\\Leaf"></SORTING_INFO>'
    return _wrap(entry, playlists=playlists, sorting_info=sorting_info)


def _sets_section() -> str:
    entry = _entry("Squarepusher", "Come On My Selector", "C:", "/:Music/:", "come_on.mp3")
    sets = '<SET NAME="RemixSet1"></SET>'
    return _wrap(entry, sets=sets)


_BUILDERS = {
    FIXTURE_MOVED_PATHS: _moved_paths,
    FIXTURE_RENAMED_FILE: _renamed_file,
    FIXTURE_DUPLICATE_RIPS: _duplicate_rips,
    FIXTURE_STEMS_AND_TEXT: _stems_and_text,
    FIXTURE_PLAYLIST_TREE: _playlist_tree,
    FIXTURE_SETS_SECTION: _sets_section,
}


def build_fixtures(target_dir: Path) -> list[Path]:
    """Write every fixture NML file (and its referenced audio stubs) under target_dir.

    Deterministic: calling this twice against an empty directory produces
    byte-identical files, so regeneration over an unmodified tool is a no-op.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, builder in _BUILDERS.items():
        path = target_dir / name
        path.write_text(builder(), encoding="utf-8", newline="")
        written.append(path)

    audio_dir = target_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    for stub_name in ("xtal.mp3", "roygbiv_final.mp3", "archangel_128.mp3", "archangel_320.mp3", "cafe.mp3", "baby.mp3", "come_on.mp3"):
        stub_path = audio_dir / stub_name
        stub_path.write_bytes(b"\x00" * 16)
        written.append(stub_path)

    return written


if __name__ == "__main__":
    import sys

    build_fixtures(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "corpus")


# --- reconnect fixtures -------------------------------------------------
#
# Written into a SIBLING directory, never under the main corpus: several
# stored cases scan the corpus directory itself, and an extra .nml there
# shifts their candidate counts, silently invalidating baselines this
# milestone does not intend to touch.
#
# The audio stubs carry no readable tags, so a disk candidate offers no
# tag-derived key at all and every reconnect case runs at
# --match-confidence filename, the only level admitting the bare-filename
# tier. This holds identically whether or not mutagen is installed: an
# unreadable stub yields empty tags either way.
#
# Stub size matters, and is not arbitrary. Traktor's FILESIZE is the audio
# payload in KILOBYTES, not the file's byte count, so a stub must be
# _RECON_STUB_KB * 1024 bytes for the collection's FILESIZE to be a
# truthful statement about the file beside it. Writing 16 bytes next to
# FILESIZE="16" made the two sides collide numerically by accident and
# encoded exactly the byte-equality assumption the cascade no longer makes:
# the size check would now, correctly, refute such a candidate.
_RECON_STUB_KB = 16

FIXTURE_RECON_STALE = "stale.nml"

_RECON_SIMPLE = ("Aphex Twin", "Xtal", "xtal_recon.mp3")
_RECON_AMBIGUOUS = ("Burial", "Archangel", "archangel_recon.mp3")
_RECON_DANGLING = ("Four Tet", "Baby", "absent_recon.mp3")


def _recon_stale() -> str:
    """One stale collection carrying all three reconnect outcomes, so a
    single scan reports a match, an ambiguity and a dangling entry
    together rather than needing three near-identical fixtures."""
    entries = ""
    for artist, title, filename in (_RECON_SIMPLE, _RECON_AMBIGUOUS, _RECON_DANGLING):
        entries += _entry(artist, title, "D:", "/:Gone/:Music/:", filename, size=str(_RECON_STUB_KB))
    return _wrap(entries)


def build_reconnect_fixtures(target_dir: Path) -> list[Path]:
    """Write the stale collection and the on-disk audio tree the reconnect
    baseline cases scan. Deterministic like build_fixtures."""
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    stale_path = target_dir / FIXTURE_RECON_STALE
    stale_path.write_text(_recon_stale(), encoding="utf-8", newline="")
    written.append(stale_path)

    # one copy -> a clean match; two copies of the same name under
    # different folders -> an ambiguity no tier can break; the dangling
    # entry's file is deliberately absent.
    for rel in (
        f"moved/{_RECON_SIMPLE[2]}",
        f"dupes/a/{_RECON_AMBIGUOUS[2]}",
        f"dupes/b/{_RECON_AMBIGUOUS[2]}",
    ):
        stub_path = target_dir / "audio" / rel
        stub_path.parent.mkdir(parents=True, exist_ok=True)
        stub_path.write_bytes(b"\x00" * (_RECON_STUB_KB * 1024))
        written.append(stub_path)

    return written
