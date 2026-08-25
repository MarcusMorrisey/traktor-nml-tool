"""splice subcommand: merge further NML files into a base NML."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..confidence import MatchConfidence, parse_match_confidence
from ..splice import ConflictRow, assemble_output
from ..rewrite import path_collides, read_and_parse_source, write_bytes_atomically, write_row_report


def _write_conflict_report(rows: list[ConflictRow], csv_path: Path | None) -> str | None:
    # A conflict report is always written, even when --on-conflict resolves
    # every conflict, so an accepted override still leaves a record of what
    # was dropped (DL-008). Shares write_row_report with build_playlist_cmd
    # so the open/DictWriter/writeheader/writerow shape has one definition.
    return write_row_report(
        rows,
        csv_path,
        fieldnames=["identity_key", "attrs", "resolution"],
        to_dict=lambda row: {"identity_key": row.identity_key, "attrs": row.attrs, "resolution": row.resolution},
        print_line=lambda row: f"conflict_key={row.identity_key} attrs={row.attrs} resolution={row.resolution}",
        label="conflict",
    )


def _handle_splice(args: argparse.Namespace) -> int:
    # Refuses output == any input path (the tool's existing dry-run
    # convention, extended here to every splice input, not just base).
    if path_collides(args.output, args.base, *args.input):
        print("output_must_differ_from_input", file=sys.stderr)
        return 2

    # Read and parse every input (base plus every --input contribution)
    # through rewrite.read_and_parse_source, so a malformed file yields
    # xml_parse_error naming that file and exit code 2 instead of an lxml
    # exception escaping this handler.
    base_result = read_and_parse_source(args.base)
    if base_result.error is not None:
        print(base_result.error, file=sys.stderr)
        return 2
    base_bytes, base_root = base_result.source_bytes, base_result.root

    contributions = []
    for path in args.input:
        contribution_result = read_and_parse_source(path)
        if contribution_result.error is not None:
            print(contribution_result.error, file=sys.stderr)
            return 2
        contributions.append((contribution_result.source_bytes.decode("utf-8"), contribution_result.root))

    confidence = parse_match_confidence(args.match_confidence) if args.match_confidence else MatchConfidence.STRICT

    result = assemble_output(
        base_bytes.decode("utf-8"), base_root, contributions, confidence, on_conflict=args.on_conflict
    )

    for key, value in result.stats.items():
        print(f"{key}={value}")
    if _write_conflict_report(result.conflict_rows, args.conflict_report) is not None:
        return 2

    if result.output is None:
        for error in result.errors:
            print(error, file=sys.stderr)
        print("splice_aborted=true", file=sys.stderr)
        return 2

    if not args.dry_run:
        # write_bytes_atomically commits through a temp file plus
        # os.replace, so an interrupted write cannot truncate an existing
        # destination (unlike a plain Path.write_bytes call). A commit
        # failure (e.g. disk full, or os.replace itself failing) is
        # reported as a diagnostic and a non-zero exit rather than an
        # escaping exception, matching every other write command's
        # error-reporting convention.
        try:
            write_bytes_atomically(args.output, result.output.encode("utf-8"))
        except OSError as exc:
            print(f"output_write_error={exc}", file=sys.stderr)
            return 2
        print(f"output_written={args.output.as_posix()}")
    return 0


def register(subparsers, handlers: dict) -> None:
    parser = subparsers.add_parser("splice", help="Merge further NML files into a base NML")
    parser.add_argument("base", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--input", action="append", dest="input", required=True, type=Path)
    parser.add_argument("--on-conflict", choices=["keep-first", "keep-last"], default=None)
    parser.add_argument("--match-confidence", choices=[level.value for level in MatchConfidence], default=None)
    parser.add_argument("--conflict-report", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    handlers["splice"] = _handle_splice
