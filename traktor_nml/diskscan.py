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



_EMPTY_TAGS = {"artist": "", "title": "", "album": "", "playtime_float": "", "bitrate": ""}


def _record_for_file(resolved: Path, file_stat, tags: Optional[dict]) -> EntryRecord:
    """The disk-side EntryRecord for one file, shared by index_scan_roots
    and index_files so a scanned file and an explicitly listed one carry
    identical fields. tags None gives empty tag fields: the file is still
    a candidate for the path and size tiers."""
    tags = tags if tags is not None else _EMPTY_TAGS
    return EntryRecord(
        entry=None,
        artist=tags.get("artist", ""),
        title=tags.get("title", ""),
        audio_id="",
        # KILOBYTES, matching the unit Traktor writes into
        # FILESIZE, so EntryRecord.filesize means one thing
        # regardless of which side produced the record. The
        # alternative - storing bytes and converting at
        # comparison time - has to infer provenance from
        # another field, and infers it silently: a candidate
        # built without that field is out by 1024x with no
        # error, only wrong answers.
        filesize=str(round(file_stat.st_size / 1024)),
        playtime_float=tags.get("playtime_float", ""),
        bitrate=tags.get("bitrate", ""),
        album=tags.get("album", ""),
        file_name=resolved.name,
        location=_placeholder_location(resolved),
        source_path=resolved,
    )


class DiskReadError(OSError):
    """A file named explicitly to index_files could not be stat()ed.

    Raised rather than counted: index_scan_roots may skip an unreadable
    file because the caller asked for whatever a walk finds, but a caller
    of index_files named every file it wants, and a list one short is
    indistinguishable from a complete one."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"cannot read {path.as_posix()}")
        self.path = path


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


def _emit_diagnostic(on_diagnostic, line: str) -> None:
    """Hand a fully formatted diagnostic line to on_diagnostic when a
    caller supplied one, or print it to stderr when it is unset. The
    branch lives in one place so index_scan_roots' two emission sites
    cannot diverge (DL-056)."""
    if on_diagnostic is not None:
        on_diagnostic(line)
    else:
        print(line, file=sys.stderr)


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
    on_diagnostic: Optional[Callable[[str], None]] = None,
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

    on_diagnostic(line), when supplied, receives the tag_reading_unavailable
    and disk_scan_progress lines instead of them being printed to stderr.

    All three default to None, and with all three unset the scan produces
    the same records, the same stats, the same stderr, and the same cache
    as a call that never mentions them. discover_tracks_cmd, the only other
    production caller, passes none of the three and has no parity-manifest
    case of its own; this default-inertness is what keeps it unchanged, by
    construction rather than by test coverage.
    """
    if not HAS_MUTAGEN:
        # Derived from the cascade table, not written out in prose. Without
        # tags every tag-derived tier is dead, and which of the remainder can
        # fire depends on the confidence level - so naming them by hand meant
        # the message went stale the moment a tier changed level. It already
        # had: it claimed plural "path-suffix tiers" at the default after
        # path_suffix_2 moved to loose.
        _emit_diagnostic(
            on_diagnostic,
            "tag_reading_unavailable=mutagen not installed; tiers still able to "
            "match, by --match-confidence level: " + _tag_free_summary(),
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
                _emit_diagnostic(
                    on_diagnostic, f"disk_scan_progress={stats['files_seen']}"
                )

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

            # Only the record construction is shared with index_files; this
            # walk keeps its own skip, dedupe, stats and cache rules, which
            # the reconnect and discover baselines pin.
            records.append(_record_for_file(resolved, file_stat, tags))
            _report_progress(on_progress, done, total, resolved, callback_every)
    finally:
        cache.flush()

    return records


def index_files(paths: Iterable[Path], cache: Optional[TagCache] = None) -> list[EntryRecord]:
    """One EntryRecord per path, in the order given, duplicates kept.

    No directory walk and no deduplication: the caller's list is the
    playlist, so its order and repetitions are the playlist's (DL-037). A
    path whose stat() fails raises DiskReadError naming it. A file whose
    tags cannot be read still yields a record, with empty tag fields. With
    cache None tags are read directly and no cache file is read or written.
    """
    records: list[EntryRecord] = []
    for path in paths:
        resolved = Path(path).resolve()
        try:
            file_stat = resolved.stat()
        except OSError:
            raise DiskReadError(resolved) from None
        # A caller-supplied cache follows index_scan_roots' refresh rule;
        # without one, tags are read directly and no cache file is left
        # behind.
        if cache is None:
            tags = _read_tags(resolved)
        elif cache.should_refresh(resolved, file_stat.st_size, file_stat.st_mtime, False):
            tags = _read_tags(resolved)
            cache.put(resolved, file_stat.st_size, file_stat.st_mtime, tags)
        else:
            tags = cache.get(resolved, file_stat.st_size, file_stat.st_mtime)
        records.append(_record_for_file(resolved, file_stat, tags))
    if cache is not None:
        cache.flush()
    return records
