"""build-playlist subcommand: synthesize an NML playlist from an external
track list matched against a base collection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..buildplaylist import UnresolvedRow, assemble_output
from ..rewrite import path_collides, read_and_parse_source, write_bytes_atomically, write_row_report
from ..spans import SpanIndex
from ..split import build_output
from ..xmlio import parse_xml_bytes


def _write_unresolved_report(rows: list[UnresolvedRow], csv_path: Path | None) -> str | None:
    # An unresolved report is always written, matching splice_cmd.py's own
    # _write_conflict_report convention (both now go through the shared
    # write_row_report): a record of what a run could not resolve is kept
    # whether or not the run itself aborted (DL-027, DL-034).
    return write_row_report(
        rows,
        csv_path,
        fieldnames=["line_number", "raw_text", "artist", "title", "kind"],
        to_dict=lambda row: {
            "line_number": row.line_number,
            "raw_text": row.raw_text,
            "artist": row.artist,
            "title": row.title,
            "kind": row.kind,
        },
        print_line=lambda row: f"unresolved line={row.line_number} kind={row.kind} text={row.raw_text!r}",
        label="unresolved",
    )


def _handle_build_playlist(args: argparse.Namespace) -> int:
    # Refuses output == base or == tracklist, via the shared path_collides
    # helper rather than write_nml_safely's extra_inputs, which exists only
    # on the attribute-patching write path this span-assembly command does
    # not use (DL-033). --unresolved-report is checked against base,
    # tracklist, and output together: it is a second destination this run
    # can write to, and a report path pointed at any of them would corrupt
    # an input or the primary output, on a run this command otherwise
    # describes as writing nothing (DL-027).
    if path_collides(args.output, args.base, args.tracklist):
        print("output_must_differ_from_input", file=sys.stderr)
        return 2
    if args.unresolved_report is not None and path_collides(
        args.unresolved_report, args.base, args.tracklist, args.output
    ):
        print("unresolved_report_must_differ_from_input", file=sys.stderr)
        return 2

    base_result = read_and_parse_source(args.base)
    if base_result.error is not None:
        print(base_result.error, file=sys.stderr)
        return 2
    base_bytes, base_root = base_result.source_bytes, base_result.root

    try:
        tracklist_bytes = args.tracklist.read_bytes()
    except OSError:
        # OSError, not just FileNotFoundError: a directory or a
        # permission-denied path must report the same clean diagnostic
        # rather than an unhandled traceback.
        print(f"input_not_found={args.tracklist.as_posix()}", file=sys.stderr)
        return 2

    try:
        # utf-8-sig transparently strips a leading UTF-8 BOM rather than
        # letting it silently corrupt the first parsed line's artist name.
        tracklist_text = tracklist_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        print(f"tracklist_decode_error={args.tracklist.as_posix()}", file=sys.stderr)
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
    if _write_unresolved_report(result.unresolved_rows, args.unresolved_report) is not None:
        return 2

    if result.output is None:
        for error in result.errors:
            print(error, file=sys.stderr)
        # same exit code as an input error (xml_parse_error, input_not_found):
        # splice_cmd.py does not distinguish these failure classes either (DL-035).
        print("build_playlist_aborted=true", file=sys.stderr)
        return 2

    output = result.output
    if not args.full_collection:
        # The normal hand-off is an importable, self-contained playlist,
        # not a copy of the caller's whole music library. Reuse split's
        # reference validation and byte-span assembly after synthesis.
        isolated_root = parse_xml_bytes(output.encode("utf-8"))
        isolated = build_output(
            output,
            isolated_root,
            [str(result.stats["playlist_name"])],
            "fail",
            SpanIndex(output, isolated_root),
        )
        if isolated.output is None:
            for error in isolated.errors:
                print(error, file=sys.stderr)
            print("build_playlist_aborted=true", file=sys.stderr)
            return 2
        output = isolated.output

    if not args.dry_run:
        try:
            write_bytes_atomically(args.output, output.encode("utf-8"))
        except OSError as exc:
            print(f"output_write_error={exc}", file=sys.stderr)
            return 2
        print(f"output_written={args.output.as_posix()}")
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
    parser.add_argument(
        "--full-collection",
        action="store_true",
        help="Keep the full source collection and playlist tree instead of the default single-playlist output.",
    )
    parser.add_argument("--allow-unmatched", action="store_true")
    parser.add_argument("--unresolved-report", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Skip the write to the NML output file. Any report or CSV side file this command writes is still written.")
    handlers["build-playlist"] = _handle_build_playlist
