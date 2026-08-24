"""Filesystem candidate index feeding the matching cascade's candidate side.

A disk-derived EntryRecord has no source element and no AUDIO_ID (that tier
is structurally unreachable from the disk side - nothing on disk carries
Traktor's internal audio identifier), so it can be fed straight into
matching.match_records as the "new" side unmodified.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Optional

from .model import EntryRecord, LocationParts
from .tagcache import TagCache

try:
    import mutagen

    HAS_MUTAGEN = True
except ImportError:  # pragma: no cover - degrade to filename/filesize matching
    HAS_MUTAGEN = False

AUDIO_EXTENSIONS = (".mp3", ".flac", ".wav", ".aiff", ".aif", ".m4a", ".ogg", ".stem.mp3", ".stem.flac")


def _has_audio_extension(path: Path) -> bool:
    """Extension check only - does not open or validate the file, so a
    renamed non-audio file with an audio-like extension is still indexed
    as a candidate and left to fail later at the tag-read stage."""
    name = path.name.lower()
    return any(name.endswith(ext) for ext in AUDIO_EXTENSIONS)


def _read_tags(path: Path) -> Optional[dict]:
    if not HAS_MUTAGEN:
        return None
    try:
        audio = mutagen.File(path, easy=True)
    except Exception:
        return None
    if audio is None:
        return None
    tags = getattr(audio, "tags", None) or {}

    def _first(key: str) -> str:
        value = tags.get(key)
        return value[0] if value else ""

    playtime = ""
    if getattr(audio, "info", None) is not None and getattr(audio.info, "length", None):
        playtime = f"{audio.info.length:.3f}"
    bitrate = ""
    if getattr(audio, "info", None) is not None and getattr(audio.info, "bitrate", None):
        bitrate = str(int(audio.info.bitrate / 1000))

    return {
        "artist": _first("artist"),
        "title": _first("title"),
        "album": _first("album"),
        "playtime_float": playtime,
        "bitrate": bitrate,
    }


def _placeholder_location(path: Path) -> LocationParts:
    # Disk-scan candidates never feed the attribute-patch write path, so this
    # LocationParts exists only to carry decoded_path for stats/CSV output.
    posix_dir = "/:" + "/:".join(path.parent.parts[1:] if path.is_absolute() else path.parent.parts) + "/:"
    return LocationParts(volume="", volumeid="", dir_value=posix_dir, file_name=path.name)


def index_scan_roots(
    scan_roots: Iterable[Path],
    cache: TagCache,
    *,
    refresh_cache: bool = False,
    progress_every: int = 500,
    stats: dict[str, int] | None = None,
) -> list[EntryRecord]:
    """Walk each scan root, deduplicate by resolved path, and yield candidates.

    Progress is emitted at intervals; unreadable files are counted in stats
    rather than aborting the walk. STEM files are indexed like any other
    audio file, not skipped.
    """
    if not HAS_MUTAGEN:
        print("tag_reading_unavailable=mutagen not installed; degrading to filename/filesize matching", file=sys.stderr)

    if stats is None:
        stats = {}
    stats.setdefault("files_seen", 0)
    stats.setdefault("duplicates_skipped", 0)
    stats.setdefault("unreadable", 0)
    stats.setdefault("cache_hits", 0)
    stats.setdefault("cache_misses", 0)

    seen: set[Path] = set()
    records: list[EntryRecord] = []

    for root in scan_roots:
        for path in sorted(Path(root).rglob("*")):
            if not path.is_file() or not _has_audio_extension(path):
                continue
            resolved = path.resolve()
            if resolved in seen:
                stats["duplicates_skipped"] += 1
                continue
            seen.add(resolved)
            stats["files_seen"] += 1
            if stats["files_seen"] % progress_every == 0:
                print(f"disk_scan_progress={stats['files_seen']}", file=sys.stderr)

            try:
                file_stat = resolved.stat()
            except OSError:
                stats["unreadable"] += 1
                continue

            if cache.should_refresh(resolved, file_stat.st_size, file_stat.st_mtime, refresh_cache):
                tags = _read_tags(resolved)
                cache.put(resolved, file_stat.st_size, file_stat.st_mtime, tags)
                stats["cache_misses"] += 1
            else:
                tags = cache.get(resolved, file_stat.st_size, file_stat.st_mtime)
                stats["cache_hits"] += 1

            if tags is None:
                stats["unreadable"] += 1
                tags = {"artist": "", "title": "", "album": "", "playtime_float": "", "bitrate": ""}

            records.append(
                EntryRecord(
                    entry=None,
                    artist=tags.get("artist", ""),
                    title=tags.get("title", ""),
                    audio_id="",
                    filesize=str(file_stat.st_size),
                    playtime_float=tags.get("playtime_float", ""),
                    bitrate=tags.get("bitrate", ""),
                    album=tags.get("album", ""),
                    file_name=resolved.name,
                    location=_placeholder_location(resolved),
                    source_path=resolved,
                )
            )

    cache.flush()
    return records
