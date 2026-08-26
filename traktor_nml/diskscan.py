"""Filesystem candidate index feeding the matching cascade's candidate side.

A disk-derived EntryRecord has no source element and no AUDIO_ID (that tier
is structurally unreachable from the disk side - nothing on disk carries
Traktor's internal audio identifier), so it can be fed straight into
matching.match_records as the "new" side unmodified.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Callable, Iterable, Optional

from .confidence import MatchConfidence
from .matching import tag_free_tiers
from .model import EntryRecord, LocationParts
from .tagcache import TagCache

try:
    import mutagen

    HAS_MUTAGEN = True
except ImportError:  # pragma: no cover - degrade to path/filename matching
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



def _tag_free_summary() -> str:
    """Which tiers survive with no readable tags, per confidence level.

    Reads the cascade table rather than restating it, so a tier that changes
    level changes this message with it.
    """
    seen: set[str] = set()
    parts = []
    for level in MatchConfidence:
        added = [name for name in tag_free_tiers(level) if name not in seen]
        seen.update(added)
        if added:
            parts.append(f"{level.value}={'+'.join(added)}")
    return "; ".join(parts) if parts else "none"


class ScanCancelled(RuntimeError):
    """Raised when a scan stops because its cancel token was signalled.

    An exception rather than a short return: a partial candidate list is
    indistinguishable from a complete one by inspection, so a caller that
    forgot to check the token would silently match a whole collection
    against a fraction of the disk and report the rest as missing. This
    cannot be ignored by accident.
    """


def _enumerate_candidates(scan_roots, stats):
    """Every audio file under the scan roots, deduplicated, in scan order.

    Split out of the indexing loop so the file count is known BEFORE any tag
    is read - a progress bar needs a denominator, and section 3.4 of the GUI
    plan requires `total` to be known before the first callback or explicitly
    None. Directory traversal is cheap next to per-file tag reading.

    Deduplication happens here, which is why the total counts the files that
    will actually be indexed rather than being an upper bound `done` could
    never reach.
    """
    seen = set()
    ordered = []
    for root in scan_roots:
        for path in sorted(Path(root).rglob("*")):
            if not path.is_file() or not _has_audio_extension(path):
                continue
            resolved = path.resolve()
            if resolved in seen:
                stats["duplicates_skipped"] += 1
                continue
            seen.add(resolved)
            ordered.append(resolved)
    return ordered


def _report_progress(on_progress, done, total, path, every):
    """Emit at most one callback per `every` files, and always the last one.

    Bounded on both sides: a callback per file would hammer a UI on a
    100,000-file library, while emitting only every Nth would leave `done`
    short of `total` whenever total is not a multiple of N - and section 3.4
    requires the final callback to fire exactly once with done == total. The
    `or` covers the last file; when total IS a multiple of `every`, both
    conditions are true for that file and it still fires once.
    """
    if on_progress is None:
        return
    if done % every == 0 or done == total:
        on_progress(done, total, path)


def index_scan_roots(
    scan_roots: Iterable[Path],
    cache: TagCache,
    *,
    refresh_cache: bool = False,
    progress_every: int = 500,
    stats: dict[str, int] | None = None,
    on_progress: Optional[Callable[[int, int, Path], None]] = None,
    cancel: Optional[threading.Event] = None,
    callback_every: int = 25,
) -> list[EntryRecord]:
    """Walk each scan root, deduplicate by resolved path, and yield candidates.

    Progress is emitted at intervals; unreadable files are counted in stats
    rather than aborting the walk. STEM files are indexed like any other
    audio file, not skipped.

    on_progress(done, total, path) reports indexing progress for a caller that
    can show it. It fires at most once per `callback_every` files and always
    once for the final file, so `done` ends equal to `total`.

    cancel is checked between files; a set token raises ScanCancelled. What
    the scan learned before that point is still flushed to the tag cache, so
    a cancelled run does not throw away reading it already paid for.

    Both default to None, and the scan then behaves exactly as it did before
    they existed: same records, same stats, same stderr, same cache.
    """
    if not HAS_MUTAGEN:
        # Derived from the cascade table, not written out in prose. Without
        # tags every tag-derived tier is dead, and which of the remainder can
        # fire depends on the confidence level - so naming them by hand meant
        # the message went stale the moment a tier changed level. It already
        # had: it claimed plural "path-suffix tiers" at the default after
        # path_suffix_2 moved to loose.
        print(
            "tag_reading_unavailable=mutagen not installed; tiers still able to "
            "match, by --match-confidence level: " + _tag_free_summary(),
            file=sys.stderr,
        )

    if stats is None:
        stats = {}
    stats.setdefault("files_seen", 0)
    stats.setdefault("duplicates_skipped", 0)
    stats.setdefault("unreadable", 0)
    stats.setdefault("cache_hits", 0)
    stats.setdefault("cache_misses", 0)

    candidates = _enumerate_candidates(scan_roots, stats)
    total = len(candidates)
    records: list[EntryRecord] = []

    # The cache is flushed even when the scan raises, so a cancelled run keeps
    # the tag reading it already did. TagCache.flush is atomic, so a partial
    # cache reloads cleanly - incomplete, never corrupt.
    try:
        for done, resolved in enumerate(candidates, start=1):
            if cancel is not None and cancel.is_set():
                raise ScanCancelled(f"scan cancelled after {done - 1} of {total} files")

            stats["files_seen"] += 1
            if stats["files_seen"] % progress_every == 0:
                print(f"disk_scan_progress={stats['files_seen']}", file=sys.stderr)

            try:
                file_stat = resolved.stat()
            except OSError:
                stats["unreadable"] += 1
                _report_progress(on_progress, done, total, resolved, callback_every)
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
            _report_progress(on_progress, done, total, resolved, callback_every)
    finally:
        cache.flush()

    return records
