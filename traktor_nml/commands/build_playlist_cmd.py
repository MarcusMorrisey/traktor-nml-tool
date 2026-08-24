"""build-playlist subcommand: synthesize an NML playlist from an external
track list matched against a base collection."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from ..buildplaylist import UnresolvedRow, assemble_output
from ..rewrite import read_and_parse_source, write_bytes_atomically


def _write_unresolved_report(rows: list[UnresolvedRow], csv_path: Path | None) -> None:
    # An unresolved report is always written, matching splice_cmd.py's own
    # _write_conflict_report convention: a record of what a run could not
    # resolve is kept whether or not the run itself aborted (DL-027, DL-034).
    for row in rows:
        print(f"unresolved line={row.line_number} kind={row.kind} text={row.raw_text!r}")
    if csv_path is not None:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["line_number", "raw_text", "artist", "title", "kind"])
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "line_number": row.line_number,
                        "raw_text": row.raw_text,
                        "artist": row.artist,
                        "title": row.title,
                        "kind": row.kind,
                    }
                )
        print(f"unresolved_report_written={csv_path}")


def _handle_build_playlist(args: argparse.Namespace) -> int:
    # Refuses output == base or == tracklist, mirroring splice_cmd.py's own
    # bespoke tuple-membership check for its multi-input shape (DL-033).
    # --unresolved-report is checked against the same protected set: it is
    # a second destination this run can write to, and a report path
    # pointed at base or tracklist would truncate an input the run is
    # supposed to leave untouched, on a run this command otherwise
    # describes as writing nothing (DL-027).
    protected = {args.base.resolve(), args.tracklist.resolve()}
    if args.output.resolve() in protected:
        print("output_must_differ_from_input", file=sys.stderr)
        return 2
    if args.unresolved_report is not None and args.unresolved_report.resolve() in protected | {args.output.resolve()}:
        print("unresolved_report_must_differ_from_input", file=sys.stderr)
        return 2

    base_result = read_and_parse_source(args.base)
    if base_result.error is not None:
        print(base_result.error, file=sys.stderr)
        return 2
    base_bytes, base_root = base_result.source_bytes, base_result.root

    try:
        tracklist_bytes = args.tracklist.read_bytes()
    except FileNotFoundError:
        print(f"input_not_found={args.tracklist}", file=sys.stderr)
        return 2

    try:
        # utf-8-sig transparently strips a leading UTF-8 BOM rather than
        # letting it silently corrupt the first parsed line's artist name.
        tracklist_text = tracklist_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        print(f"tracklist_decode_error={args.tracklist}", file=sys.stderr)
        return 2

    result = assemble_output(
        base_bytes.decode("utf-8"),
        base_root,
        tracklist_text,
        args.name,
        target_folder=args.target_folder,
        allow_unmatched=args.allow_unmatched,
    )

    for key, value in result.stats.items():
        print(f"{key}={value}")
    _write_unresolved_report(result.unresolved_rows, args.unresolved_report)

    if result.output is None:
        for error in result.errors:
            print(error, file=sys.stderr)
        # same exit code as an input error (xml_parse_error, input_not_found):
        # splice_cmd.py does not distinguish these failure classes either (DL-035).
        print("build_playlist_aborted=true", file=sys.stderr)
        return 2

    if not args.dry_run:
        try:
            write_bytes_atomically(args.output, result.output.encode("utf-8"))
        except OSError as exc:
            print(f"output_write_error={exc}", file=sys.stderr)
            return 2
        print(f"output_written={args.output}")
    return 0


def register(subparsers, handlers: dict) -> None:
    """Register the build-playlist subparser. No --match-confidence option
    is exposed: resolution always runs at a fixed MatchConfidence.LOOSE,
    since a text-only track list leaves every stricter tier unreachable
    (DL-032)."""
    parser = subparsers.add_parser(
        "build-playlist",
        help="Build an NML playlist from an external track list matched against a base collection",
    )
    parser.add_argument("base", type=Path)
    parser.add_argument("tracklist", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--target-folder", default=None)
    parser.add_argument("--allow-unmatched", action="store_true")
    parser.add_argument("--unresolved-report", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    handlers["build-playlist"] = _handle_build_playlist
