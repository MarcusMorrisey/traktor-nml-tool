"""split subcommand: partition one NML into several outputs by playlist."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..split import build_output
from ..spans import SpanIndex
from ..rewrite import read_and_parse_source, write_bytes_atomically


def _parse_groups(raw_groups: list[list[str]] | None) -> list[tuple[Path, list[str]]]:
    """Parse repeated --group PATH NAMES entries into (output_path,
    playlist_names) pairs; NAMES is comma-separated, and an empty segment
    (e.g. a trailing comma) is dropped rather than producing a blank
    playlist name to look up."""
    groups = []
    for output_path, names_csv in raw_groups or []:
        names = [name for name in names_csv.split(",") if name]
        groups.append((Path(output_path), names))
    return groups


def _handle_split(args: argparse.Namespace) -> int:
    groups = _parse_groups(args.group)
    if not groups:
        print("at_least_one_group_required", file=sys.stderr)
        return 2

    output_paths = [path for path, _ in groups]
    if args.input.resolve() in {p.resolve() for p in output_paths}:
        print("output_must_differ_from_input", file=sys.stderr)
        return 2

    read_result = read_and_parse_source(args.input)
    if read_result.error is not None:
        print(read_result.error, file=sys.stderr)
        return 2
    source_bytes, root = read_result.source_bytes, read_result.root
    source_text = source_bytes.decode("utf-8")

    # One SpanIndex built once for the whole document, rather than once
    # per group, and handed to build_output on every group iteration.
    span_index = SpanIndex(source_text, root)

    outcomes = []
    for output_path, names in groups:
        outcome = build_output(source_text, root, names, args.dangling_policy, span_index)
        outcomes.append((output_path, outcome))
        print(f"group_output={output_path.as_posix()}")
        for key, value in outcome.stats.items():
            print(f"  {key}={value}")
        for error in outcome.errors:
            print(f"  {error}", file=sys.stderr)

    if any(outcome.output is None for _, outcome in outcomes):
        print("split_aborted=true", file=sys.stderr)
        return 2

    # Each destination is committed through write_bytes_atomically (temp
    # file plus os.replace), so a failure mid-write leaves that
    # destination holding either its previous bytes or the complete new
    # bytes, never a truncated partial write. This loop is not
    # transactional across the several group outputs: a failure partway
    # through still leaves earlier groups written, the bounded tradeoff
    # DL-022 records rather than an oversight - cross-file staging and
    # commit is new machinery this milestone does not add.
    if not args.dry_run:
        for output_path, outcome in outcomes:
            try:
                write_bytes_atomically(output_path, outcome.output.encode("utf-8"))
            except OSError as exc:
                print(f"output_write_error={exc}", file=sys.stderr)
                return 2
            print(f"output_written={output_path.as_posix()}")
    return 0


def register(subparsers, handlers: dict) -> None:
    parser = subparsers.add_parser("split", help="Partition one NML into several outputs by playlist")
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--group",
        nargs=2,
        action="append",
        metavar=("OUTPUT_PATH", "PLAYLIST_NAMES"),
        help="Repeatable: an output path paired with a comma-separated list of playlist names.",
    )
    parser.add_argument(
        "--dangling-policy", choices=["exclude", "pull-in", "fail"], default="exclude",
    )
    parser.add_argument("--dry-run", action="store_true")
    handlers["split"] = _handle_split
