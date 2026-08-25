"""preview-diff and rewrite subcommands (rule-based rewriting)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..model import (
    RewriteRule,
    all_entries,
    apply_rules,
    collection_entries,
    entry_label,
    normalize_dir_prefix,
    parse_location_element,
    parse_primary_key,
)
from ..rewrite import _collect_rewrite_patches, rewrite_nml, write_nml_safely
from ..xmlio import XML_PARSE_ERROR, parse_xml


def add_rule_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--old-volume")
    parser.add_argument("--old-dir-prefix")
    parser.add_argument("--new-volume")
    parser.add_argument("--new-dir-prefix")
    parser.add_argument("--new-volumeid")


def add_multi_rule_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--rule",
        nargs=4,
        action="append",
        metavar=("OLD_VOLUME", "OLD_DIR_PREFIX", "NEW_VOLUME", "NEW_DIR_PREFIX"),
        help="Repeatable rewrite rule. Prefixes may be human paths or Traktor-encoded paths.",
    )
    parser.add_argument(
        "--rule-with-volumeid",
        nargs=5,
        action="append",
        metavar=("OLD_VOLUME", "OLD_DIR_PREFIX", "NEW_VOLUME", "NEW_DIR_PREFIX", "NEW_VOLUMEID"),
        help="Repeatable rewrite rule with explicit VOLUMEID override.",
    )


def build_rules(args: argparse.Namespace) -> list[RewriteRule]:
    # Rules are tried in the order built here; apply_rules returns the
    # first match, so an earlier --rule/--rule-with-volumeid takes
    # precedence over a later one covering an overlapping prefix.
    rules: list[RewriteRule] = []

    if getattr(args, "rule", None):
        for old_volume, old_dir, new_volume, new_dir in args.rule:
            rules.append(
                RewriteRule(
                    old_volume=old_volume,
                    old_dir_prefix=normalize_dir_prefix(old_dir),
                    new_volume=new_volume,
                    new_dir_prefix=normalize_dir_prefix(new_dir),
                )
            )

    if getattr(args, "rule_with_volumeid", None):
        for old_volume, old_dir, new_volume, new_dir, new_volumeid in args.rule_with_volumeid:
            rules.append(
                RewriteRule(
                    old_volume=old_volume,
                    old_dir_prefix=normalize_dir_prefix(old_dir),
                    new_volume=new_volume,
                    new_dir_prefix=normalize_dir_prefix(new_dir),
                    new_volumeid=new_volumeid,
                )
            )

    if not rules:
        required = ["old_volume", "old_dir_prefix", "new_volume", "new_dir_prefix"]
        missing = [name for name in required if not getattr(args, name, None)]
        if missing:
            raise ValueError(
                "either provide a complete single rule via "
                "--old-volume/--old-dir-prefix/--new-volume/--new-dir-prefix "
                "or provide one or more --rule/--rule-with-volumeid entries"
            )
        rules.append(
            RewriteRule(
                old_volume=args.old_volume,
                old_dir_prefix=normalize_dir_prefix(args.old_dir_prefix),
                new_volume=args.new_volume,
                new_dir_prefix=normalize_dir_prefix(args.new_dir_prefix),
                new_volumeid=args.new_volumeid,
            )
        )

    return rules


def preview_diff_nml(root, rules: list[RewriteRule], limit: int) -> int:
    coll_entries = collection_entries(root)
    coll_entry_ids = {id(entry) for entry in coll_entries}
    old_to_new_key: dict[str, str] = {}

    collection_location_changes: list[tuple[str, str, str]] = []
    other_location_changes: list[tuple[str, str, str]] = []
    primarykey_changes: list[tuple[str, str, str]] = []

    for entry in coll_entries:
        loc_elem = entry.find("LOCATION")
        if loc_elem is None:
            continue
        old_loc = parse_location_element(loc_elem)
        new_loc, changed = apply_rules(old_loc, rules)
        if changed:
            old_to_new_key[old_loc.primary_key] = new_loc.primary_key
            collection_location_changes.append(
                (entry_label(entry), str(old_loc.decoded_path), str(new_loc.decoded_path))
            )

    for entry in all_entries(root):
        if id(entry) not in coll_entry_ids:
            loc_elem = entry.find("LOCATION")
            if loc_elem is not None:
                old_loc = parse_location_element(loc_elem)
                new_loc, changed = apply_rules(old_loc, rules)
                if changed:
                    other_location_changes.append(
                        (entry_label(entry), str(old_loc.decoded_path), str(new_loc.decoded_path))
                    )

        pk_elem = entry.find("PRIMARYKEY")
        if pk_elem is None:
            continue

        old_key = pk_elem.attrib.get("KEY", "")
        new_key = old_to_new_key.get(old_key)
        if new_key is None:
            try:
                old_loc = parse_primary_key(old_key)
            except ValueError:
                continue
            new_loc, changed = apply_rules(old_loc, rules)
            if not changed:
                continue
            new_key = new_loc.primary_key

        primarykey_changes.append((entry_label(entry), old_key, new_key))

    print(f"collection_location_changes={len(collection_location_changes)}")
    print(f"other_location_changes={len(other_location_changes)}")
    print(f"primarykey_changes={len(primarykey_changes)}")

    if collection_location_changes:
        print("sample_collection_location_changes:")
        for label, before, after in collection_location_changes[:limit]:
            print(f"- {label}")
            print(f"  before={before}")
            print(f"  after={after}")

    if other_location_changes:
        print("sample_other_location_changes:")
        for label, before, after in other_location_changes[:limit]:
            print(f"- {label}")
            print(f"  before={before}")
            print(f"  after={after}")

    if primarykey_changes:
        print("sample_primarykey_changes:")
        for label, before, after in primarykey_changes[:limit]:
            print(f"- {label}")
            print(f"  before={before}")
            print(f"  after={after}")

    return 0


def _handle_preview_diff(args: argparse.Namespace) -> int:
    try:
        tree = parse_xml(args.input)
    except FileNotFoundError:
        print(f"input_not_found={args.input.as_posix()}", file=sys.stderr)
        return 2
    except XML_PARSE_ERROR as exc:
        print(f"xml_parse_error={args.input.as_posix()}: {exc}", file=sys.stderr)
        return 2
    try:
        rules = build_rules(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return preview_diff_nml(tree.getroot(), rules, limit=args.limit)


def _handle_rewrite(args: argparse.Namespace) -> int:
    try:
        rules = build_rules(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    def _collect_patches(root):
        patches, stats = _collect_rewrite_patches(root, rules)
        return patches, stats, None

    def mutate_tree(root, dry_run):
        stats = rewrite_nml(root, rules, dry_run=dry_run)
        return stats, None

    return write_nml_safely(args.input, args.output, args.dry_run, _collect_patches, mutate_tree)


def register(subparsers, handlers: dict) -> None:
    preview_parser = subparsers.add_parser("preview-diff", help="Preview path rewrites without writing")
    preview_parser.add_argument("input", type=Path)
    add_rule_args(preview_parser)
    add_multi_rule_args(preview_parser)
    preview_parser.add_argument("--limit", type=int, default=10)
    handlers["preview-diff"] = _handle_preview_diff

    rewrite_parser = subparsers.add_parser("rewrite", help="Rewrite paths in an NML file")
    rewrite_parser.add_argument("input", type=Path)
    rewrite_parser.add_argument("output", type=Path)
    add_rule_args(rewrite_parser)
    add_multi_rule_args(rewrite_parser)
    rewrite_parser.add_argument("--dry-run", action="store_true", help="Skip the write to the NML output file. Any report or CSV side file this command writes is still written.")
    handlers["rewrite"] = _handle_rewrite
