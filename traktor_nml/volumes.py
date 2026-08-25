"""Explicit VOLUME/VOLUMEID identity for a disk-scan root (DL-005).

A rewritten LOCATION with a wrong or empty VOLUMEID produces a PRIMARYKEY
Traktor cannot resolve, and reconnection runs precisely because the recorded
paths no longer describe reality - so inferring identity from those same
stale paths would be inference from the least trustworthy field in the file.
Inference is accepted only when a prefix scan of the old collection yields a
single distinct VOLUME/VOLUMEID pair; every other case is a hard error.
"""

# parse_volume_map (the --volume-map argparse handler) and
# resolve_volume_identity share the same Path-normalisation step
# (DL-005), so a map entry authored with any separator style still
# matches scan_root at lookup time.

from __future__ import annotations

from typing import Optional
from pathlib import Path

from .model import EntryRecord, LocationParts


class VolumeIdentityError(ValueError):
    pass


def resolve_volume_identity(
    scan_root: Path,
    old_records: list[EntryRecord],
    volume_map: dict[str, tuple[str, str]] | None,
) -> tuple[str, str]:
    """Return (volume, volumeid) for scan_root.

    volume_map, when given, maps a scan root string (as passed on the
    command line) to an explicit (volume, volumeid) pair and always wins.
    Otherwise every old-collection record whose decoded path starts under
    scan_root is inspected; if they agree on exactly one (volume, volumeid)
    pair, that pair is used. Any other outcome - no observations, or more
    than one distinct pair - raises, naming scan_root.
    """
    # Both --volume-map entries (raw CLI strings) and scan_root are
    # normalised through Path before comparison, so "C:\music", "C:/music"
    # and "C:\music\" all key the same override regardless of which
    # separator/trailing-slash style the map was authored with or the root
    # was passed as.
    root_key = str(Path(scan_root))
    if volume_map and root_key in volume_map:
        return volume_map[root_key]

    # decoded_dir is a PurePosixPath built from Traktor's own DIR encoding
    # and is volume-relative (it never carries a drive/mount prefix), while
    # scan_root is a mount-absolute filesystem path - the two are not
    # comparable as a raw string prefix. Instead, compare on path components,
    # after stripping scan_root's own drive/anchor (which decoded_dir can
    # never contain either): an old record is "under" scan_root when
    # scan_root's own (anchor-stripped) components are a PREFIX of
    # decoded_dir's components once both are rooted at their volume, matched
    # whole segments only, so a scan root named Music never matches a
    # decoded path under Musicology, and a scan root D:\\Music\\Artist never
    # matches an unrelated record whose deep folder path happens to end in
    # ...\\Music\\Artist.
    scan_root_parts = Path(scan_root).parts
    if Path(scan_root).anchor:
        scan_root_parts = scan_root_parts[1:]
    scan_parts = [part.rstrip("/\\") for part in scan_root_parts]
    observed: set[tuple[str, str]] = set()
    if scan_parts:
        for record in old_records:
            decoded_parts = [part for part in record.location.decoded_dir.parts if part != "/"]
            if decoded_parts[:len(scan_parts)] == scan_parts:
                observed.add((record.location.volume, record.location.volumeid))

    if len(observed) == 1:
        return next(iter(observed))

    raise VolumeIdentityError(
        f"volume_identity_ambiguous scan_root={Path(scan_root).as_posix()} observed_pairs={sorted(observed)}; "
        "pass --volume-map"
    )


def parse_volume_map(entries: list[list[str]] | None) -> dict[str, tuple[str, str]]:
    """Parse repeatable --volume-map SCAN_ROOT VOLUME VOLUMEID triples."""
    mapping: dict[str, tuple[str, str]] = {}
    for scan_root, volume, volumeid in entries or []:
        mapping[str(Path(scan_root))] = (volume, volumeid)
    return mapping


def local_path_for_location(
    location: LocationParts, known_mounts: dict[tuple[str, str], list[Path]]
) -> Optional[Path]:
    """Invert location_from_disk_path: resolve location's recorded
    VOLUME/VOLUMEID plus its volume-relative decoded_path back to the
    absolute on-disk path it names, against mount anchors this run has
    established explicitly (known_mounts, keyed by the same (VOLUME,
    VOLUMEID) pair resolve_volume_identity produces).

    Returns the resolved path only when exactly one anchor registered for
    location's own pair joins with decoded_path to a readable file.
    Returns None when the pair appears in no mapping, when no candidate
    anchor resolves, and when two distinct anchors for one pair both
    resolve - never guesses an anchor from the VOLUME string or a POSIX
    mount-directory convention, since that would be inference from the
    same stale decoded path DL-005 already rules out, and its failure mode
    is a wrong file rather than a missing one.
    """
    anchors = known_mounts.get((location.volume, location.volumeid))
    if not anchors:
        return None
    relative = location.decoded_path
    relative_parts = relative.parts[1:] if relative.parts and relative.parts[0] == "/" else relative.parts
    resolved = {
        candidate for candidate in (Path(anchor, *relative_parts) for anchor in anchors) if candidate.is_file()
    }
    if len(resolved) == 1:
        return next(iter(resolved))
    return None
