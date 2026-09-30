"""splice subcommand: merge further NML files into a base NML."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..confidence import MatchConfidence, parse_match_confidence
from ..splice import ConflictRow, SettledRow, assemble_output
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


def _print_settled_outliers(rows: list[SettledRow]) -> None:
    """One line per settled group whose measured gap exceeds the band.

    The settled count itself is printed with the rest of the stats above,
    because it is one of the run's counts. This is the reading beside it:
    a group the rule answered where the two numbers are far enough apart
    that the operator may want to know which one the output carries - a
    playtime_float 3,516 seconds apart shows as a wrong track length in
    Traktor until it re-analyses (DL-330, DL-331).

    The record that won is named by both halves of the pair the row
    carries, winner_input and winner_key: the two members of a settled
    group describe the one LOCATION and so share the one primary key, so
    winner_key on its own names neither of them, while the index says
    which collection the kept numbers were read from (DL-148, DL-150).

    A run whose rule settled nothing, and a run whose settled groups are
    all within the band, print no line at all rather than a header with
    nothing under it.

    One line per reading rather than per group: a group reading past the
    band on two measured attributes has two facts to state, and a line
    naming one attribute is what a caller parsing this output splits on.
    The line is prefixed settled_outlier so it is greppable beside the
    key=value stats above it without a header standing over it.

    Every value is read off result.settled_rows; nothing here recomputes
    a gap or a count (DL-215).
    """
    for row in rows:
        winner_input, winner_key = row.winner
        for reading in row.outliers:
            print(
                "settled_outlier"
                f" key={row.identity_key}"
                f" attr={reading.attr}"
                f" low={reading.low}"
                f" high={reading.high}"
                f" relative_gap={reading.relative_gap:.4f}"
                f" winner_input={winner_input}"
                f" winner_key={winner_key}"
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
        base_bytes.decode("utf-8"), base_root, contributions, confidence,
        on_conflict=args.on_conflict, reconstruct=args.reconstruct_playlists,
    )

    for key, value in result.stats.items():
        print(f"{key}={value}")
    # Under the stats block, so groups_settled_by_rule is read first and
    # the lines below it are the reading of that count.
    # Before the conflict report is written, so a run that refuses on a
    # report it could not write has still printed what the rule settled
    # (DL-008's precedent, DL-329).
    _print_settled_outliers(result.settled_rows)
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
    parser.add_argument(
        "--reconstruct-playlists", action="store_true",
        help="Rebuild a base playlist in place from same-named playlists in the inputs when their "
             "contents differ, instead of importing a renamed copy beside it. The base playlist keeps "
             "its own node, UUID and folder position.",
    )
    parser.add_argument("--conflict-report", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Skip the write to the NML output file. Any report or CSV side file this command writes is still written.")
    handlers["splice"] = _handle_splice
