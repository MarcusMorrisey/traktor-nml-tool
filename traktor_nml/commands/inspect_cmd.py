"""inspect and encode-dir subcommands."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from ..model import (
    all_entries,
    collection_entries,
    location_rows,
    normalize_dir_prefix,
    playlist_entries,
)
from ..xmlio import XML_PARSE_ERROR, parse_xml


def inspect_nml(root, limit: int, csv_path: Path | None) -> int:
    """Print collection/playlist counts and up to limit sample rows, then
    optionally write every row (not just the printed sample) to csv_path
    via the shared location_rows/csv.DictWriter pattern."""
    coll_entries = collection_entries(root)
    playlist_refs = playlist_entries(root)
    all_doc_entries = all_entries(root)

    coll_locations = [e for e in coll_entries if e.find("LOCATION") is not None]
    coll_primarykeys = [e for e in coll_entries if e.find("PRIMARYKEY") is not None]
    playlist_primarykeys = [e for e in playlist_refs if e.find("PRIMARYKEY") is not None]

    print(f"root_version={root.attrib.get('VERSION', '')}")
    head = root.find("HEAD")
    print(f"program={'' if head is None else head.attrib.get('PROGRAM', '')}")
    print(f"collection_entries={len(coll_entries)}")
    print(f"collection_entries_with_location={len(coll_locations)}")
    print(f"collection_entries_with_primarykey={len(coll_primarykeys)}")
    print(f"playlist_entry_refs={len(playlist_refs)}")
    print(f"playlist_primarykeys={len(playlist_primarykeys)}")
    print(f"all_entry_nodes_in_document={len(all_doc_entries)}")

    all_rows = location_rows(coll_locations)
    rows = all_rows[:limit]

    for row in rows:
        print(
            f"sample artist={row['artist']!r} title={row['title']!r} "
            f"volume={row['volume']!r} dir={row['dir']!r} file={row['file']!r}"
        )

    if csv_path is not None:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(all_rows[0].keys()) if all_rows else [])
            if all_rows:
                writer.writeheader()
                writer.writerows(all_rows)
        print(f"csv_written={csv_path}")

    return 0


def _handle_inspect(args: argparse.Namespace) -> int:
    try:
        tree = parse_xml(args.input)
    except FileNotFoundError:
        print(f"input_not_found={args.input}", file=sys.stderr)
        return 2
    except XML_PARSE_ERROR as exc:
        print(f"xml_parse_error={args.input}: {exc}", file=sys.stderr)
        return 2
    return inspect_nml(tree.getroot(), limit=args.limit, csv_path=args.csv)


def _handle_encode_dir(args: argparse.Namespace) -> int:
    print(normalize_dir_prefix(args.path_value))
    return 0


def register(subparsers, handlers: dict) -> None:
    inspect_parser = subparsers.add_parser("inspect", help="Inspect an NML file")
    inspect_parser.add_argument("input", type=Path)
    inspect_parser.add_argument("--limit", type=int, default=10)
    inspect_parser.add_argument("--csv", type=Path)
    handlers["inspect"] = _handle_inspect

    encode_parser = subparsers.add_parser("encode-dir", help="Encode a human path to Traktor DIR format")
    encode_parser.add_argument("path_value")
    handlers["encode-dir"] = _handle_encode_dir
