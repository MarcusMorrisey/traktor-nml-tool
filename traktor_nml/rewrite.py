"""Non-collection cascade and the shared read-parse-patch-write skeleton.

Rule-based and compare-based rewriting both need to walk every entry outside
the collection updating LOCATION and PRIMARYKEY, and both need to read a
source file, parse it, patch it, and write it back exactly once (DL-001).
process_non_collection_entries takes an EntryResolver so the two callers
differ only in how an old key or location resolves to its replacement, and
write_nml_safely takes lxml-path and stdlib-path builder callables so both
existing write commands share one read/print/write shell.
"""

from __future__ import annotations

import csv
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Protocol, TypeVar

from .confidence import MatchConfidence
from .matching import KeyProvider, build_new_indexes, match_records
from .reconnect import enforce_one_to_one
from .model import (
    EntryRecord,
    ElemPatch,
    LocationParts,
    all_entries,
    apply_rules,
    collection_entries,
    collection_records,
    loc_attr_changes,
    parse_location_element,
    parse_primary_key,
    write_location_element,
)
from .textpatch import apply_text_patches, location_patch, primarykey_patch
from .xmlio import ET, HAS_LXML, XML_PARSE_ERROR, parse_xml, parse_xml_bytes, write_traktor_xml


class EntryResolver(Protocol):
    """Resolves an old-side LOCATION and PRIMARYKEY to their replacements.

    locate's second return value doubles as "should this be counted and
    written" - rule-based resolvers count on a rule match, compare-based
    resolvers count on an actual attribute difference, matching each
    strategy's pre-extraction behavior exactly.
    """

    location_stat: str
    """Stats-dict key incremented once per LOCATION this resolver
    actually rewrites - a rule-based resolver and a compare-based
    resolver each name their own key, so print_stats_and_samples reports
    the correct label for whichever strategy produced this resolver."""

    def locate(self, old_loc: LocationParts) -> tuple[LocationParts, bool]: ...

    def key_of(self, old_key: str) -> Optional[str]: ...

    def fallback_key(self, old_key: str) -> Optional[str]: ...


@dataclass
class RuleEntryResolver:
    rules: list
    old_to_new_key: dict[str, str]
    location_stat: str = "history_locations_rewritten"

    def locate(self, old_loc: LocationParts) -> tuple[LocationParts, bool]:
        return apply_rules(old_loc, self.rules)

    def key_of(self, old_key: str) -> Optional[str]:
        return self.old_to_new_key.get(old_key)

    def fallback_key(self, old_key: str) -> Optional[str]:
        try:
            old_pk_loc = parse_primary_key(old_key)
        except ValueError:
            return None
        new_loc, changed = apply_rules(old_pk_loc, self.rules)
        return new_loc.primary_key if changed else None


@dataclass
class CompareEntryResolver:
    mapping: dict[str, EntryRecord]
    location_stat: str = "other_locations_rewritten"

    def locate(self, old_loc: LocationParts) -> tuple[LocationParts, bool]:
        new_record = self.mapping.get(old_loc.primary_key)
        if new_record is None:
            return old_loc, False
        return new_record.location, bool(loc_attr_changes(old_loc, new_record.location))

    def key_of(self, old_key: str) -> Optional[str]:
        new_record = self.mapping.get(old_key)
        return None if new_record is None else new_record.primary_key

    def fallback_key(self, old_key: str) -> Optional[str]:
        return None


def process_non_collection_entries(
    root: ET.Element,
    coll_ids: set[int],
    resolver: EntryResolver,
    stats: dict[str, int],
    *,
    dry_run: bool = False,
    patches: list[ElemPatch] | None = None,
) -> None:
    """Update every entry outside the collection through resolver.

    When patches is not None, attribute changes are appended to it (lxml
    path). When patches is None and dry_run is False, changes are applied
    directly to the tree (stdlib fallback path).
    """
    for entry in all_entries(root):
        if id(entry) in coll_ids:
            continue
        loc_elem = entry.find("LOCATION")
        if loc_elem is not None:
            old_loc = parse_location_element(loc_elem)
            new_loc, counted = resolver.locate(old_loc)
            if counted:
                stats[resolver.location_stat] += 1
                ch = loc_attr_changes(old_loc, new_loc)
                if patches is not None:
                    if ch:
                        patches.append(location_patch(loc_elem, old_loc, ch))
                elif not dry_run:
                    write_location_element(loc_elem, new_loc)
        pk_elem = entry.find("PRIMARYKEY")
        if pk_elem is None:
            continue
        old_key = pk_elem.attrib.get("KEY", "")
        new_key = resolver.key_of(old_key)
        if new_key is not None:
            stats["primarykeys_updated_from_collection"] += 1
            if patches is not None:
                patches.append(primarykey_patch(pk_elem, old_key, new_key))
            elif not dry_run:
                pk_elem.attrib["KEY"] = new_key
            continue
        new_key = resolver.fallback_key(old_key)
        if new_key is not None:
            stats["primarykeys_rewritten_directly"] += 1
            if patches is not None:
                patches.append(primarykey_patch(pk_elem, old_key, new_key))
            elif not dry_run:
                pk_elem.attrib["KEY"] = new_key
        else:
            stats["primarykeys_unchanged"] += 1


def _empty_rule_stats() -> dict[str, int]:
    return {
        "collection_locations_rewritten": 0,
        "history_locations_rewritten": 0,
        "primarykeys_updated_from_collection": 0,
        "primarykeys_rewritten_directly": 0,
        "primarykeys_unchanged": 0,
    }


def _empty_compare_stats() -> dict[str, int]:
    # No primarykeys_rewritten_directly key here: CompareEntryResolver.fallback_key
    # always returns None (compare-based rewriting has no direct-rule fallback),
    # so that stat is never incremented on this path and printing it would add
    # a key the pre-extraction compare-based commands never emitted.
    return {
        "collection_locations_rewritten": 0,
        "other_locations_rewritten": 0,
        "primarykeys_updated_from_collection": 0,
        "primarykeys_unchanged": 0,
    }


def rewrite_nml(root: ET.Element, rules: list, dry_run: bool) -> dict[str, int]:
    """Apply rule-based rewriting: rewrite each collection LOCATION whose
    old value matches a rule, record the old-to-new PRIMARYKEY
    substitution for every changed collection location, then redirect
    every non-collection PRIMARYKEY/LOCATION through the same rules via
    the shared cascade in process_non_collection_entries."""
    stats = _empty_rule_stats()
    coll = collection_entries(root)
    old_to_new_key: dict[str, str] = {}
    for entry in coll:
        loc_elem = entry.find("LOCATION")
        if loc_elem is None:
            continue
        old_loc = parse_location_element(loc_elem)
        new_loc, changed = apply_rules(old_loc, rules)
        if changed:
            old_to_new_key[old_loc.primary_key] = new_loc.primary_key
            stats["collection_locations_rewritten"] += 1
            if not dry_run:
                write_location_element(loc_elem, new_loc)
    resolver = RuleEntryResolver(rules=rules, old_to_new_key=old_to_new_key)
    process_non_collection_entries(root, {id(e) for e in coll}, resolver, stats, dry_run=dry_run)
    return stats


def warn_if_refutation_disabled(args) -> bool:
    """Read --no-refute, announcing it when set.

    A run that silently ignores size and duration contradictions can commit
    a rewrite onto a file the collection's own numbers say is the wrong
    one, so the switch says so on every run rather than only in --help.
    Returns whether to refute, for passing straight into the cascade.
    """
    if not getattr(args, "no_refute", False):
        return True
    print(
        "refutation_disabled=size and duration contradictions will be ignored; "
        "a candidate the collection's own FILESIZE/PLAYTIME_FLOAT contradict can now win a match",
        file=sys.stderr,
    )
    return False


def add_no_refute_argument(parser) -> None:
    parser.add_argument(
        "--no-refute",
        action="store_true",
        help="Do not drop candidates whose size or duration contradicts the collection entry. "
        "The tolerances are calibrated against one real library; use this if they are rejecting "
        "files you know are correct (a run reports how many it withdrew as refuted=N).",
    )

def rewrite_from_collection_compare(
    old_root: ET.Element, new_root: ET.Element, dry_run: bool, confidence: MatchConfidence,
    key_providers: list[KeyProvider] = (),
    refute: bool = True,
) -> tuple[dict[str, int], list[tuple[str, str, str, str]]]:
    """Apply compare-based rewriting: match old collection records
    against a newer collection's records via the tiered cascade, rewrite
    each matched collection LOCATION whose attributes actually changed,
    then redirect every non-collection reference through the resulting
    old-to-new mapping via the shared cascade."""
    old_records = collection_records(old_root)
    new_records = collection_records(new_root)
    indexes = build_new_indexes(new_records, confidence, key_providers)
    mapping, match_stats, samples = match_records(
        old_records, new_records, confidence, key_providers, indexes=indexes, refute=refute
    )
    mapping, match_stats, _collided = enforce_one_to_one(
        mapping, match_stats, old_records, indexes, confidence, key_providers
    )
    stats = {**_empty_compare_stats(), **match_stats}
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
    return stats, samples


def _collect_rewrite_patches(root: ET.Element, rules: list) -> tuple[list[ElemPatch], dict[str, int]]:
    stats = _empty_rule_stats()
    patches: list[ElemPatch] = []
    coll = collection_entries(root)
    old_to_new_key: dict[str, str] = {}
    for entry in coll:
        loc_elem = entry.find("LOCATION")
        if loc_elem is None:
            continue
        old_loc = parse_location_element(loc_elem)
        new_loc, changed = apply_rules(old_loc, rules)
        if changed:
            old_to_new_key[old_loc.primary_key] = new_loc.primary_key
            stats["collection_locations_rewritten"] += 1
            ch = loc_attr_changes(old_loc, new_loc)
            if ch:
                patches.append(location_patch(loc_elem, old_loc, ch))
    resolver = RuleEntryResolver(rules=rules, old_to_new_key=old_to_new_key)
    process_non_collection_entries(root, {id(e) for e in coll}, resolver, stats, patches=patches)
    return patches, stats


def _collect_compare_patches(
    old_root: ET.Element, old_records: list[EntryRecord], mapping: dict[str, EntryRecord]
) -> tuple[list[ElemPatch], dict[str, int]]:
    stats = _empty_compare_stats()
    patches: list[ElemPatch] = []
    for record in old_records:
        new_record = mapping.get(record.primary_key)
        if new_record is None:
            continue
        loc_elem = record.entry.find("LOCATION")
        if loc_elem is not None:
            ch = loc_attr_changes(record.location, new_record.location)
            if ch:
                stats["collection_locations_rewritten"] += 1
                patches.append(location_patch(loc_elem, record.location, ch))
    resolver = CompareEntryResolver(mapping=mapping)
    process_non_collection_entries(
        old_root, {id(r.entry) for r in old_records}, resolver, stats, patches=patches
    )
    return patches, stats


@dataclass
class ReadParseResult:
    source_bytes: Optional[bytes]
    root: Optional[ET.Element]
    error: Optional[str]  # a pre-formatted diagnostic line, e.g. "input_not_found=path"


def read_and_parse_source(path: Path) -> ReadParseResult:
    """Read path as bytes and parse it, reporting input_not_found for a
    missing file and xml_parse_error naming the path for a malformed one.
    write_nml_safely's own lxml branch uses this so the diagnostics have
    one definition, and the span-transplantation commands (splice, split)
    reach the same behavior without passing through the patch-and-write
    skeleton write_nml_safely wraps."""
    try:
        source_bytes = path.read_bytes()
    except FileNotFoundError:
        return ReadParseResult(None, None, f"input_not_found={path.as_posix()}")
    try:
        root = parse_xml_bytes(source_bytes)
    except XML_PARSE_ERROR as exc:
        return ReadParseResult(None, None, f"xml_parse_error={path.as_posix()}: {exc}")
    return ReadParseResult(source_bytes, root, None)


def write_bytes_atomically(output: Path, data: bytes) -> None:
    """Write data to output through a temp file plus os.replace, under a
    public name so the splice and split commands write through the same
    primitive apply_and_write and the stdlib branch already use, rather
    than each command committing its own plain, truncating write."""
    # write_bytes/open("wb") truncate an existing destination in place, so a
    # write that fails partway (disk full, process killed) can leave a
    # truncated file where a valid collection used to stand. Writing to a
    # temp file in the same directory and renaming over the destination
    # means the destination only ever shows the old complete file or the new
    # complete file, never a partial one - os.replace is atomic on both
    # POSIX and Windows for same-volume renames.
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(output.parent), prefix=f".{output.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp_name, str(output))
    except BaseException:
        try:
            os.remove(tmp_name)
        except OSError:
            pass
        raise


def path_collides(candidate: Path, *protected: Path) -> bool:
    """True if candidate resolves to any of protected. write_nml_safely's
    own extra_inputs parameter covers this for the attribute-patching write
    path; splice/split/build-playlist take the byte-span assembly path
    instead and share this helper for their own output/report-path
    collision refusals, resolving each protected path once per call rather
    than each command re-deriving its own set-membership check."""
    resolved = candidate.resolve()
    return any(resolved == p.resolve() for p in protected)


_Row = TypeVar("_Row")


def write_row_report(
    rows: Iterable[_Row],
    csv_path: Optional[Path],
    fieldnames: list[str],
    to_dict: Callable[[_Row], dict[str, Any]],
    print_line: Callable[[_Row], str],
    label: str,
) -> Optional[str]:
    """Print each row via print_line, then - if csv_path is given - write
    it as CSV (DictWriter, header row, newline="", UTF-8) and print
    "{label}_report_written=path". Shared by splice_cmd.py and
    build_playlist_cmd.py's conflict/unresolved reports, which otherwise
    hand-roll the identical open/DictWriter/writeheader/writerow shape.
    Returns None on success, or an already-stderr-printed error string if
    csv_path's parent doesn't exist or the write otherwise fails - callers
    return exit code 2 on a non-None result, matching every other
    input/output error in these commands."""
    rows = list(rows)
    for row in rows:
        print(print_line(row))
    if csv_path is not None:
        try:
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(to_dict(row))
        except OSError as exc:
            error = f"{label}_report_write_error={exc}"
            print(error, file=sys.stderr)
            return error
        print(f"{label}_report_written={csv_path.as_posix()}")
    return None


def apply_and_write(source_bytes: bytes, patches: list[ElemPatch], output: Path) -> None:
    # Traktor's current collection/history files declare UTF-8. Keeping the
    # source string intact means this re-encodes to exactly the same bytes
    # except for the requested XML-escaped attribute values.
    patched = apply_text_patches(source_bytes.decode("utf-8"), patches)
    write_bytes_atomically(output, patched.encode("utf-8"))


def print_stats_and_samples(
    stats: dict[str, int], samples: list[tuple[str, str, str, str]] | None, limit: int = 10
) -> None:
    for key, value in stats.items():
        print(f"{key}={value}")
    if samples:
        print("sample_matches:")
        for label, before, after, matched_by in samples[:limit]:
            print(f"- {label}")
            print(f"  matched_by={matched_by}")
            print(f"  before={before}")
            print(f"  after={after}")


# Callables a caller of write_nml_safely supplies:
#   collect_patches(root) -> (patches, stats, samples)          [lxml path]
#   mutate_tree(root, dry_run) -> (stats, samples)               [stdlib path]
CollectPatchesFn = Callable[[ET.Element], tuple[list[ElemPatch], dict[str, int], list]]
MutateTreeFn = Callable[[ET.Element, bool], tuple[dict[str, int], list]]


def write_nml_safely(
    input_path: Path,
    output_path: Path,
    dry_run: bool,
    collect_patches: CollectPatchesFn,
    mutate_tree: MutateTreeFn,
    extra_inputs: tuple[Path, ...] = (),
) -> int:
    """Read source bytes, parse, patch, print stats, and write once.

    Refuses to write when output_path resolves to input_path or any of
    extra_inputs (existing tool convention). Both existing write commands
    (rewrite, rewrite-from-collection-compare) are expressed as callers of
    this helper, one supplying collect_patches for the lxml path and
    mutate_tree for the stdlib fallback.
    """
    if output_path.resolve() in {input_path.resolve(), *(p.resolve() for p in extra_inputs)}:
        print("output_must_differ_from_input", file=sys.stderr)
        return 2

    if HAS_LXML:
        read_result = read_and_parse_source(input_path)
        if read_result.error is not None:
            print(read_result.error, file=sys.stderr)
            return 2
        source_bytes, root = read_result.source_bytes, read_result.root
        patches, stats, samples = collect_patches(root)
        print_stats_and_samples(stats, samples)
        if not dry_run:
            try:
                apply_and_write(source_bytes, patches, output_path)
            except (UnicodeDecodeError, ValueError) as exc:
                print(f"text_patch_error={exc}", file=sys.stderr)
                return 2
            print(f"output_written={output_path.as_posix()}")
        return 0

    try:
        tree = parse_xml(input_path)
    except FileNotFoundError:
        print(f"input_not_found={input_path.as_posix()}", file=sys.stderr)
        return 2
    except XML_PARSE_ERROR as exc:
        print(f"xml_parse_error={input_path.as_posix()}: {exc}", file=sys.stderr)
        return 2
    root = tree.getroot()
    stats, samples = mutate_tree(root, dry_run)
    print_stats_and_samples(stats, samples)
    if not dry_run:
        write_traktor_xml(root, output_path, write_bytes=write_bytes_atomically)
        print(f"output_written={output_path.as_posix()}")
    return 0
