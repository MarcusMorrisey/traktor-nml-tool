"""Printless reconnection core: match an old collection's tracks against
disk-scan candidates and return typed results.

commands/reconnect_cmd.py holds argparse wiring only; the pipeline lives
here and prints nothing. A GUI review table needs the mapping and the
ambiguity rows as objects while a run is in progress, and a transcript
parsed after the fact arrives too late for that. run_reconnection returns a
ReconnectResult, and scan_reconnect_candidates/rewrite_from_reconnect wrap
it with the CSV write and the typed-error mapping each command needs,
also as results rather than prints. reconnect_render turns these into
buffered stdout/stderr lines and an exit code.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .shared_args import resolve_confidence, should_refute
from .diskscan import index_scan_roots
from .model import EntryRecord, collection_records, loc_attr_changes, write_location_element
from .reconnect import location_from_disk_path, resolve_reconnection
from .rewrite import (
    CompareEntryResolver,
    WriteOutcome,
    _collect_compare_patches,
    plan_and_write_nml,
    process_non_collection_entries,
)
from .tagcache import TagCache
from .volumes import VolumeIdentityError, parse_volume_map, resolve_volume_identity
from .xmlio import XML_PARSE_ERROR, parse_xml

try:
    # fingerprint.py is the M-005 acoustic-fingerprint key provider; it may
    # not exist yet when this module is developed concurrently with M-005.
    # Importing it defensively keeps every other subcommand (this module is
    # reachable from commands/__init__.py, which imports every command
    # module at CLI startup) working even when fingerprint.py, pyacoustid
    # and fpcalc are absent - --fingerprint simply becomes unavailable
    # until M-005 lands, rather than the whole CLI failing to import.
    from .fingerprint import (
        FPCALC_TIMEOUT_SECONDS,
        FpcalcSession,
        fingerprint_key_provider,
        fingerprint_unavailable_reason,
    )
except ImportError:  # pragma: no cover - fingerprint tier lands in M-005
    fingerprint_key_provider = None
    fingerprint_unavailable_reason = None
    FpcalcSession = None
    FPCALC_TIMEOUT_SECONDS = 30.0


class _FingerprintUnavailable(RuntimeError):
    """--fingerprint was requested but fingerprint_key_provider is None -
    fingerprint.py itself wasn't importable, not merely one of its
    runtime dependencies missing. Distinct from the
    fingerprint_dependency_missing warning, which fires when the module
    imported fine but pyacoustid/fpcalc/chromaprint are not usable."""
    pass


@dataclass(frozen=True)
class ReconnectResult:
    """Everything one reconnection pass produced: the primary-key-to-
    winning-EntryRecord mapping, its stats, the rows a caller may export
    as an ambiguity CSV, the old records the mapping was matched against,
    and warnings - run-derived notices, currently the fingerprint
    dependency reason - that travel with the result instead of printing
    to stderr mid-pipeline. A GUI review table reads this
    directly."""

    mapping: dict[str, EntryRecord]
    stats: dict[str, int]
    ambiguity_rows: list[dict[str, str]]
    old_records: list[EntryRecord]
    warnings: list[str] = field(default_factory=list)
    # Every diagnostic index_scan_roots would have printed to stderr,
    # captured in emission order via the on_diagnostic callback instead
    # (DL-056). A sequence, not a set or mapping, because
    # tag_reading_unavailable must precede the first disk_scan_progress
    # line and the progress lines are ordered by file.
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScanReconnectResult:
    """One scan-reconnect-candidates pass. Exactly one of result and
    error is non-None; csv_path is non-None only alongside a non-None
    result, because the CSV is written after run_reconnection returns.
    diagnostics holds whatever index_scan_roots emitted before a
    volume_identity_error or fingerprint_unavailable error was raised -
    it is empty when result is set (the diagnostics then live on
    result.diagnostics instead) and empty for input_not_found or
    xml_parse_error, which occur before any scan runs.
    """

    # error carries one of input_not_found=, xml_parse_error=,
    # volume_identity_error= or fingerprint_unavailable= - the same four
    # typed failures the renderer maps to exit code 2.
    result: Optional[ReconnectResult]
    error: Optional[str]
    csv_path: Optional[Path]
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class RewriteReconnectResult:
    """One rewrite-from-reconnect pass. outcome and error are never both
    non-None: a WriteOutcome carries its own error field for write-path
    failures, and this error field is only for a failure that came out of
    the reconnection callback before plan_and_write_nml could produce an
    outcome at all. csv_path is non-None only alongside a non-None
    reconnect. diagnostics holds whatever index_scan_roots emitted before
    a volume_identity_error or fingerprint_unavailable error was raised -
    it is empty when reconnect is set (the diagnostics then live on
    reconnect.diagnostics instead).
    """

    # outcome is None only when error is set: a volume_identity_error or
    # fingerprint_unavailable raised out of the reconnection callback
    # before plan_and_write_nml's own WriteOutcome could be built, so
    # there is nothing to hold its error/exit_code fields instead.
    outcome: Optional[WriteOutcome]
    reconnect: Optional[ReconnectResult]
    csv_path: Optional[Path]
    error: Optional[str]
    diagnostics: tuple[str, ...] = ()


def _resolve_volume_identities_and_mounts(
    args: argparse.Namespace, old_records: list[EntryRecord]
) -> tuple[dict[Path, tuple[str, str]], dict[tuple[str, str], list[Path]]]:
    """Resolve each scan root's volume identity once, up front: both the
    fingerprint tier's old-side resolver and the candidate-side LOCATION
    re-encoding reuse the same resolved identities rather than resolving
    twice.
    """
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
    return volume_identities, known_mounts


def _build_fingerprint_tier(
    args: argparse.Namespace,
    cache: TagCache,
    candidates: list[EntryRecord],
    known_mounts: dict[tuple[str, str], list[Path]],
):
    """Build the fingerprint key provider when --fingerprint is set, or
    return an empty tier when it is not. The returned session (or None)
    is the caller's to terminate once resolve_reconnection has finished
    with it - this function only opens it, because the fingerprint
    provider's provide() closure fingerprints old-side records lazily
    during matching, after this function has already returned.
    """
    key_providers = []
    fingerprint_stats: dict[str, int] = {}
    warnings: list[str] = []
    if not getattr(args, "fingerprint", False):
        return key_providers, fingerprint_stats, warnings, None

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
        warnings.append(
            f"fingerprint_dependency_missing={unavailable}; "
            "--fingerprint tier will find no matches"
        )
    # The session owns the fpcalc child, so a per-file timeout is
    # enforceable and a caller can terminate one mid-fingerprint.
    fpcalc_session = FpcalcSession(timeout=getattr(args, "fpcalc_timeout", FPCALC_TIMEOUT_SECONDS))
    key_providers.append(
        fingerprint_key_provider(cache, candidates, fingerprint_stats, known_mounts, fpcalc_session)
    )
    return key_providers, fingerprint_stats, warnings, fpcalc_session


def _reencode_winning_locations(
    mapping: dict[str, EntryRecord], volume_identities: dict[Path, tuple[str, str]]
) -> None:
    """Re-encode each winning candidate's real absolute path into a
    proper LOCATION using its scan root's resolved volume identity - the
    placeholder LocationParts a disk-scan candidate carries has no real
    VOLUME/VOLUMEID and is never written as-is.
    """
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


def run_reconnection(
    args: argparse.Namespace,
    old_root,
    *,
    on_progress: Optional[Callable[[int, int, Path], None]] = None,
    cancel=None,
    diagnostics: Optional[list[str]] = None,
) -> ReconnectResult:
    """Run the whole reconnection pipeline and return a ReconnectResult.

    on_progress and cancel are forwarded verbatim to index_scan_roots,
    which already accepts both; both default to None so the CLI path
    indexes exactly as it does without them, and a GUI gets live indexing
    progress and a cancel token without bypassing this core.
    Neither parameter has an in-repo caller yet - both argparse handlers
    pass neither - and that absence is intentional: this is the channel
    a future GUI review table is meant to call once it exists, not dead
    code to remove (DL-054).
    ScanCancelled propagates rather than becoming a field on the result:
    a short candidate list is indistinguishable from a complete one, so a
    partial result would report most of the collection as missing - a
    wrong answer delivered confidently.

    diagnostics, when supplied, is the caller's own list and this
    function appends into it rather than creating its own - so the
    diagnostics collected before a later VolumeIdentityError or
    _FingerprintUnavailable raise still exist in the caller's scope after
    the raise propagates and no ReconnectResult is ever constructed. When
    omitted a fresh list is created, and ReconnectResult.diagnostics is
    populated from it exactly as before.
    """
    # Volume identities are resolved once here and reused by both the
    # fingerprint tier (_build_fingerprint_tier's known_mounts) and the
    # candidate-side LOCATION re-encoding below, so a core-boundary
    # redesign must not reintroduce a second resolution (ref: DL-046).
    old_records = collection_records(old_root)
    cache = TagCache(args.cache)
    if diagnostics is None:
        diagnostics = []
    candidates = index_scan_roots(
        args.scan_roots, cache, refresh_cache=args.refresh_cache,
        on_progress=on_progress, cancel=cancel,
        on_diagnostic=diagnostics.append,
    )
    confidence = resolve_confidence(args)

    volume_identities, known_mounts = _resolve_volume_identities_and_mounts(args, old_records)
    key_providers, fingerprint_stats, warnings, fpcalc_session = _build_fingerprint_tier(
        args, cache, candidates, known_mounts
    )
    try:
        # fpcalc_session, when the fingerprint tier is active, is opened
        # by _build_fingerprint_tier above and its child process must not
        # outlive this function: resolve_reconnection is the last
        # consumer (its provide() closure fingerprints old-side records
        # lazily during matching), so the session is terminated here
        # regardless of how matching finishes.
        mapping, stats, ambiguity_rows = resolve_reconnection(
            old_records, candidates, confidence, key_providers,
            refute=should_refute(args),
        )
    finally:
        if fpcalc_session is not None:
            fpcalc_session.terminate()
    stats = {**fingerprint_stats, **stats}

    _reencode_winning_locations(mapping, volume_identities)

    cache.flush()
    return ReconnectResult(mapping, stats, ambiguity_rows, old_records, warnings, tuple(diagnostics))


def _write_ambiguity_csv(rows: list[dict[str, str]], csv_path: Path) -> None:
    fieldnames = list(rows[0].keys()) if rows else ["artist", "title", "old_path", "reason"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if rows:
            writer.writeheader()
            writer.writerows(rows)


def scan_reconnect_candidates(
    args: argparse.Namespace,
    *,
    on_progress: Optional[Callable[[int, int, Path], None]] = None,
    cancel=None,
) -> ScanReconnectResult:
    """Run one scan-reconnect-candidates pass, printless.

    on_progress and cancel pass straight through to run_reconnection.
    Writes the ambiguity CSV when args.csv is set, after
    run_reconnection has returned, and records the written path on the
    result rather than printing it. Writes to neither stream.
    """
    # Both typed failures below are returned as an
    # error=<key>=<value> string; the renderer, not this function,
    # decides how they reach stdout/stderr and maps them to exit code 2.
    try:
        old_tree = parse_xml(args.old_input)
    except FileNotFoundError:
        return ScanReconnectResult(None, f"input_not_found={args.old_input.as_posix()}", None)
    except XML_PARSE_ERROR as exc:
        return ScanReconnectResult(None, f"xml_parse_error={args.old_input.as_posix()}: {exc}", None)

    diagnostics: list[str] = []
    try:
        result = run_reconnection(
            args, old_tree.getroot(), on_progress=on_progress, cancel=cancel, diagnostics=diagnostics,
        )
    except VolumeIdentityError as exc:
        return ScanReconnectResult(None, f"volume_identity_error={exc}", None, tuple(diagnostics))
    except _FingerprintUnavailable as exc:
        return ScanReconnectResult(None, f"fingerprint_unavailable={exc}", None, tuple(diagnostics))

    csv_path = None
    if args.csv is not None:
        _write_ambiguity_csv(result.ambiguity_rows, args.csv)
        csv_path = args.csv
    return ScanReconnectResult(result, None, csv_path)


def _apply_mapping_stdlib(
    old_root, old_records: list[EntryRecord], mapping: dict[str, EntryRecord], stats: dict[str, int], dry_run: bool
) -> None:
    """Both writers - this stdlib path and rewrite.py's compare-based
    lxml path - must share one PRIMARYKEY/entry-rewrite rule, so every
    non-collection entry here is handed to CompareEntryResolver, the same
    resolver rewrite.py uses. Each matched record's LOCATION is rewritten
    directly (rather than through the resolver) since a disk-scan match
    carries no compare-report entry of its own.
    """
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


def rewrite_from_reconnect(
    args: argparse.Namespace,
    *,
    on_progress: Optional[Callable[[int, int, Path], None]] = None,
    cancel=None,
) -> RewriteReconnectResult:
    """Run one rewrite-from-reconnect pass, printless.

    on_progress and cancel reach run_reconnection through the callback.
    A mutable holder dict with keys reconnect and csv_path,
    both initially None, is populated by the callback and read after
    plan_and_write_nml returns. The write order inside the callback fixes
    the holder's meaning in every case: run_reconnection returns first
    and the holder's reconnect key is set immediately, then the CSV is
    written and csv_path is set - so there is no state in which csv_path
    is set while reconnect is None, and no partial ReconnectResult is
    ever stored. ScanCancelled escapes rather than becoming a field.

    Both the tag cache (via run_reconnection's cache.flush()) and the
    ambiguity CSV are written on every call regardless of args.dry_run:
    dry_run governs only the final write_nml_safely/plan_and_write_nml
    step, and neither the cache nor the CSV is this command's declared
    output.
    """
    holder: dict[str, object] = {"reconnect": None, "csv_path": None}
    diagnostics: list[str] = []

    def _collect_patches(old_root):
        result = run_reconnection(
            args, old_root, on_progress=on_progress, cancel=cancel, diagnostics=diagnostics,
        )
        holder["reconnect"] = result
        patches, apply_stats = _collect_compare_patches(old_root, result.old_records, result.mapping)
        merged_stats = {**apply_stats, **result.stats}
        if args.csv is not None:
            _write_ambiguity_csv(result.ambiguity_rows, args.csv)
            holder["csv_path"] = args.csv
        return patches, merged_stats, []

    def mutate_tree(old_root, dry_run):
        result = run_reconnection(
            args, old_root, on_progress=on_progress, cancel=cancel, diagnostics=diagnostics,
        )
        holder["reconnect"] = result
        merged_stats = {
            "collection_locations_rewritten": 0,
            "other_locations_rewritten": 0,
            "primarykeys_updated_from_collection": 0,
            "primarykeys_unchanged": 0,
            **result.stats,
        }
        _apply_mapping_stdlib(old_root, result.old_records, result.mapping, merged_stats, dry_run)
        if args.csv is not None:
            _write_ambiguity_csv(result.ambiguity_rows, args.csv)
            holder["csv_path"] = args.csv
        return merged_stats, []

    try:
        outcome = plan_and_write_nml(args.old_input, args.output, args.dry_run, _collect_patches, mutate_tree)
    except VolumeIdentityError as exc:
        return RewriteReconnectResult(None, None, None, f"volume_identity_error={exc}", tuple(diagnostics))
    except _FingerprintUnavailable as exc:
        return RewriteReconnectResult(None, None, None, f"fingerprint_unavailable={exc}", tuple(diagnostics))

    return RewriteReconnectResult(outcome, holder["reconnect"], holder["csv_path"], None)
