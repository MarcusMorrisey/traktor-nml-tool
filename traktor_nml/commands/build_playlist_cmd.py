"""build-playlist subcommand: synthesize an NML playlist from an external
track list matched against a base collection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..buildplaylist import UnresolvedRow, assemble_output
from ..playlistinput import CSV_COLUMNS, InputFormat, InputReadError, read_input
from ..rewrite import path_collides, read_and_parse_source, write_bytes_atomically, write_row_report
from ..spans import SpanIndex
from ..split import build_output
from ..xmlio import parse_xml_bytes


def _write_unresolved_report(
    rows: list[UnresolvedRow], csv_path: Path | None, input_format: InputFormat
) -> str | None:
    # A folder row's line_number is the file's position in name order, so
    # a folder run labels it position=; every other format keeps line=, so
    # a text run's stdout replays the corpus (DL-300). The CSV column stays
    # line_number for every format.
    label = "position" if input_format is InputFormat.FOLDER else "line"
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
        print_line=lambda row: f"unresolved {label}={row.line_number} kind={row.kind} text={row.raw_text!r}",
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

    # Base first, then the input: the order the refusals are checked in,
    # which the text corpus replays (DL-279). read_input is the reader the
    # GUI's _run_build_playlist calls as well, so both surfaces refuse an
    # unreadable input with the same code (DL-262, DL-281).
    # "auto" leaves detection to the suffix; any other value names the format.
    fmt = None if args.input_format == "auto" else InputFormat(args.input_format)
    try:
        input_read = read_input(args.tracklist, fmt)
    except InputReadError as exc:
        print(exc.code, file=sys.stderr)
        return 2

    result = assemble_output(
        base_bytes.decode("utf-8"),
        base_root,
        input_read.candidates,
        args.name,
        target_folder=args.target_folder,
        allow_unmatched=args.allow_unmatched,
    )

    # Printed ahead of the stats and only for non-text input (DL-294): a
    # text run's stdout stays byte-identical to the corpus (DL-279, DL-280),
    # and a cp1252 fallback is named where the operator reads the counts
    # (DL-283).
    if input_read.format is not InputFormat.TEXT:
        print(f"input_format={input_read.format.value}")
        print(f"input_encoding={input_read.encoding}")
    for key, value in result.stats.items():
        print(f"{key}={value}")
    if _write_unresolved_report(result.unresolved_rows, args.unresolved_report, input_read.format) is not None:
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
    is exposed: resolution always runs at a fixed MatchConfidence.LOOSE for
    every input format, which already admits every stricter tier a
    file-derived candidate can reach (DL-032, DL-276)."""
    csv_columns = ", ".join(
        f"{column.header}{'' if column.required else ' (optional)'}" for column in CSV_COLUMNS
    )
    parser = subparsers.add_parser(
        "build-playlist",
        help="Build an NML playlist from a track list, CSV, M3U/M3U8 playlist or folder matched against a base collection",
    )
    parser.add_argument("base", type=Path)
    parser.add_argument(
        "tracklist",
        type=Path,
        help="A plain-text 'Artist - Title' list, a .csv, an M3U or M3U8 playlist, or a folder whose own audio files are read in name order.",
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--input-format",
        choices=["auto", "text", "csv", "m3u", "folder"],
        default="auto",
        help=f"Read the input as this format instead of detecting it from the suffix. CSV columns: {csv_columns}.",
    )
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
