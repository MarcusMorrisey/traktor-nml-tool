"""scan-reconnect-candidates and rewrite-from-reconnect subcommands."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from ..diskscan import index_scan_roots
from ..model import EntryRecord, collection_records, loc_attr_changes, write_location_element
from ..reconnect import location_from_disk_path, resolve_reconnection
from ..rewrite import (
    CompareEntryResolver,
    _collect_compare_patches,
    process_non_collection_entries,
    write_nml_safely,
)
from ..tagcache import TagCache
from ..volumes import VolumeIdentityError, parse_volume_map, resolve_volume_identity
from ..xmlio import XML_PARSE_ERROR, parse_xml
from .compare_cmd import add_confidence_args, resolve_confidence

try:
    # fingerprint.py is the M-005 acoustic-fingerprint key provider; it may
    # not exist yet when this module is developed concurrently with M-005.
    # Importing it defensively keeps every other subcommand (this module is
    # auto-imported at CLI startup, see commands/__init__.py) working even
    # when fingerprint.py, pyacoustid and fpcalc are absent - --fingerprint
    # simply becomes unavailable until M-005 lands, rather than the whole
    # CLI failing to import.
    from ..fingerprint import fingerprint_key_provider, fingerprint_unavailable_reason
except ImportError:  # pragma: no cover - fingerprint tier lands in M-005
    fingerprint_key_provider = None
    fingerprint_unavailable_reason = None


class _FingerprintUnavailable(RuntimeError):
    pass


def add_reconnect_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scan-root",
        type=Path,
        action="append",
        dest="scan_roots",
        required=True,
        help="Filesystem root to scan for candidate audio files (repeatable).",
    )
    parser.add_argument(
        "--volume-map",
        nargs=3,
        action="append",
        metavar=("SCAN_ROOT", "VOLUME", "VOLUMEID"),
        help="Explicit VOLUME/VOLUMEID for a scan root (repeatable); required when the "
        "prefix scan of the old collection cannot resolve a single unambiguous pair.",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path(".traktor_nml_tagcache.json"),
        help="Disk-scan tag cache path. Written/updated as scan roots are indexed, "
        "independently of --dry-run: --dry-run only suppresses writes to the output "
        "NML, not this cache file.",
    )
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--csv", type=Path)
    parser.add_argument(
        "--fingerprint",
        action="store_true",
        help="Enable the acoustic-fingerprint match tier (requires pyacoustid, the fpcalc binary, and the chromaprint shared library); "
        "opt-in and off by default since these are optional dependencies.",
    )
    add_confidence_args(parser)


def _write_ambiguity_csv(rows: list[dict[str, str]], csv_path: Path) -> None:
    fieldnames = list(rows[0].keys()) if rows else ["artist", "title", "old_path", "reason"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if rows:
            writer.writeheader()
            writer.writerows(rows)
    print(f"csv_written={csv_path.as_posix()}")


def _run_reconnection(
    args: argparse.Namespace, old_root
) -> tuple[dict[str, EntryRecord], dict[str, int], list[dict[str, str]], list[EntryRecord]]:
    old_records = collection_records(old_root)
    cache = TagCache(args.cache)
    candidates = index_scan_roots(args.scan_roots, cache, refresh_cache=args.refresh_cache)
    confidence = resolve_confidence(args)

    # Volume identities are resolved once, up front, before any key
    # provider is built: both the fingerprint tier's old-side resolver
    # below and the candidate-side LOCATION re-encoding further down this
    # function reuse the same resolved identities, rather than resolving
    # twice.
    volume_map = parse_volume_map(args.volume_map)
    volume_identities: dict[Path, tuple[str, str]] = {}
    for scan_root in args.scan_roots:
        volume_identities[Path(scan_root)] = resolve_volume_identity(scan_root, old_records, volume_map)

    # known_mounts anchors each scan root at its own filesystem anchor (the
    # drive letter or POSIX root, e.g. "C:\\" or "/"), never at scan_root
    # itself - decoded_path is volume-relative (relative to the volume
    # root), not relative to an arbitrary scan-root subdirectory, so
    # anchoring at scan_root would reconstruct the wrong absolute path for
    # every record whose file sits outside that particular subdirectory.
    known_mounts: dict[tuple[str, str], list[Path]] = {}
    for scan_root, identity in volume_identities.items():
        anchor = Path(scan_root).anchor
        if anchor:
            known_mounts.setdefault(identity, []).append(Path(anchor))

    key_providers = []
    fingerprint_stats: dict[str, int] = {}
    if getattr(args, "fingerprint", False):
        if fingerprint_key_provider is None:
            raise _FingerprintUnavailable(
                "fingerprint_key_provider unavailable (traktor_nml.fingerprint not installed)"
            )
        unavailable = fingerprint_unavailable_reason()
        if unavailable is not None:
            # Every way this tier can be unusable degrades to matching
            # nothing, so an undiagnosed run looks exactly like one that
            # searched and found no candidates. The reason is named rather
            # than the dependency set listed, because the three pieces fail
            # independently and "pyacoustid/fpcalc not available" is wrong
            # advice when the missing piece is the chromaprint library and
            # both of those are installed.
            print(
                f"fingerprint_dependency_missing={unavailable}; "
                "--fingerprint tier will find no matches",
                file=sys.stderr,
            )
        key_providers.append(fingerprint_key_provider(cache, candidates, fingerprint_stats, known_mounts))

    mapping, stats, ambiguity_rows = resolve_reconnection(
        old_records, candidates, confidence, key_providers
    )
    stats = {**fingerprint_stats, **stats}

    # Re-encode each winning candidate's real absolute path into a proper
    # LOCATION using its scan root's resolved volume identity - the
    # placeholder LocationParts a disk-scan candidate carries has no real
    # VOLUME/VOLUMEID and is never written as-is.
    for candidate in mapping.values():
        if candidate.source_path is None:
            continue
        for scan_root, identity in volume_identities.items():
            try:
                candidate.source_path.relative_to(scan_root.resolve())
            except ValueError:
                continue
            candidate.location = location_from_disk_path(candidate.source_path, *identity)
            break

    cache.flush()
    return mapping, stats, ambiguity_rows, old_records


def _apply_mapping_stdlib(
    old_root, old_records: list[EntryRecord], mapping: dict[str, EntryRecord], stats: dict[str, int], dry_run: bool
) -> None:
    for record in old_records:
        new_record = mapping.get(record.primary_key)
        if new_record is None:
            continue
        ch = loc_attr_changes(record.location, new_record.location)
        if ch:
            stats["collection_locations_rewritten"] += 1
            if not dry_run:
                loc_elem = record.entry.find("LOCATION")
                if loc_elem is not None:
                    write_location_element(loc_elem, new_record.location)
    resolver = CompareEntryResolver(mapping=mapping)
    process_non_collection_entries(
        old_root, {id(r.entry) for r in old_records}, resolver, stats, dry_run=dry_run
    )


def _handle_scan_reconnect_candidates(args: argparse.Namespace) -> int:
    try:
        old_tree = parse_xml(args.old_input)
    except FileNotFoundError:
        print(f"input_not_found={args.old_input.as_posix()}", file=sys.stderr)
        return 2
    except XML_PARSE_ERROR as exc:
        print(f"xml_parse_error={args.old_input.as_posix()}: {exc}", file=sys.stderr)
        return 2
    try:
        mapping, stats, ambiguity_rows, _old_records = _run_reconnection(args, old_tree.getroot())
    except VolumeIdentityError as exc:
        print(f"volume_identity_error={exc}", file=sys.stderr)
        return 2
    except _FingerprintUnavailable as exc:
        print(f"fingerprint_unavailable={exc}", file=sys.stderr)
        return 2

    print(f"reconnectable={len(mapping)}")
    for key, value in stats.items():
        print(f"{key}={value}")
    if args.csv is not None:
        _write_ambiguity_csv(ambiguity_rows, args.csv)
    return 0


def _handle_rewrite_from_reconnect(args: argparse.Namespace) -> int:
    def _collect_patches(old_root):
        mapping, stats, ambiguity_rows, old_records = _run_reconnection(args, old_root)
        patches, apply_stats = _collect_compare_patches(old_root, old_records, mapping)
        merged_stats = {**apply_stats, **stats}
        if args.csv is not None:
            _write_ambiguity_csv(ambiguity_rows, args.csv)
        return patches, merged_stats, []

    def mutate_tree(old_root, dry_run):
        mapping, stats, ambiguity_rows, old_records = _run_reconnection(args, old_root)
        merged_stats = {
            "collection_locations_rewritten": 0,
            "other_locations_rewritten": 0,
            "primarykeys_updated_from_collection": 0,
            "primarykeys_unchanged": 0,
            **stats,
        }
        _apply_mapping_stdlib(old_root, old_records, mapping, merged_stats, dry_run)
        if args.csv is not None:
            _write_ambiguity_csv(ambiguity_rows, args.csv)
        return merged_stats, []

    try:
        return write_nml_safely(args.old_input, args.output, args.dry_run, _collect_patches, mutate_tree)
    except VolumeIdentityError as exc:
        print(f"volume_identity_error={exc}", file=sys.stderr)
        return 2
    except _FingerprintUnavailable as exc:
        print(f"fingerprint_unavailable={exc}", file=sys.stderr)
        return 2


def register(subparsers, handlers: dict) -> None:
    scan_parser = subparsers.add_parser(
        "scan-reconnect-candidates",
        help="Match an old collection's tracks against disk-scan candidates without writing",
    )
    scan_parser.add_argument("old_input", type=Path)
    add_reconnect_args(scan_parser)
    handlers["scan-reconnect-candidates"] = _handle_scan_reconnect_candidates

    rewrite_parser = subparsers.add_parser(
        "rewrite-from-reconnect",
        help="Rewrite an old collection's LOCATIONs and PRIMARYKEYs from a disk scan",
    )
    rewrite_parser.add_argument("old_input", type=Path)
    rewrite_parser.add_argument("output", type=Path)
    rewrite_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stats without writing the output NML. Note: the --cache tag cache "
        "and the --csv ambiguity report are still written, since neither is the "
        "command's declared output - the cache is a scan speed-up and the report "
        "is a record of what the run saw.",
    )
    add_reconnect_args(rewrite_parser)
    handlers["rewrite-from-reconnect"] = _handle_rewrite_from_reconnect
