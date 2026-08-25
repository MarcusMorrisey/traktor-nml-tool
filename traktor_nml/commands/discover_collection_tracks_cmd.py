"""Rank collection entries for an external track list without altering the NML."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

from ..discovery import rank_collection_candidates
from ..model import collection_records
from ..rewrite import path_collides, read_and_parse_source, write_bytes_atomically
from ..tracklist import parse_tracklist


def _report_bytes(matches) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "line_number",
            "requested_artist",
            "requested_title",
            "candidate_artist",
            "candidate_title",
            "candidate_path",
            "candidate_primary_key",
            "score",
            "artist_score",
            "title_score",
        ],
    )
    writer.writeheader()
    for match in matches:
        candidate = match.candidate
        writer.writerow(
            {
                "line_number": match.line.line_number,
                "requested_artist": match.line.artist,
                "requested_title": match.line.title,
                "candidate_artist": "" if candidate is None else candidate.artist,
                "candidate_title": "" if candidate is None else candidate.title,
                "candidate_path": "" if candidate is None else str(candidate.location.decoded_path),
                "candidate_primary_key": "" if candidate is None else candidate.primary_key,
                "score": f"{match.score:.3f}",
                "artist_score": f"{match.artist_score:.3f}",
                "title_score": f"{match.title_score:.3f}",
            }
        )
    return output.getvalue().encode("utf-8")


def _handle_discover_collection_tracks(args: argparse.Namespace) -> int:
    if path_collides(args.output, args.collection, args.tracklist):
        print("output_must_differ_from_input", file=sys.stderr)
        return 2
    collection_result = read_and_parse_source(args.collection)
    if collection_result.error is not None:
        print(collection_result.error, file=sys.stderr)
        return 2
    try:
        tracklist_text = args.tracklist.read_bytes().decode("utf-8-sig")
    except OSError:
        print(f"input_not_found={args.tracklist}", file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        print(f"tracklist_decode_error={args.tracklist}", file=sys.stderr)
        return 2

    lines, unparseable = parse_tracklist(tracklist_text)
    matches = rank_collection_candidates(
        lines, collection_records(collection_result.root), max_candidates=args.max_candidates, min_score=args.min_score
    )
    print(f"collection_entries={len(collection_records(collection_result.root))}")
    print(f"lines_read={len(lines) + len(unparseable)}")
    print(f"unparseable_lines={len(unparseable)}")
    print(f"review_candidates={sum(match.candidate is not None for match in matches)}")
    print(f"no_candidate_rows={sum(match.candidate is None for match in matches)}")
    try:
        write_bytes_atomically(args.output, _report_bytes(matches))
    except OSError as exc:
        print(f"output_write_error={exc}", file=sys.stderr)
        return 2
    print(f"report_written={args.output}")
    return 0


def register(subparsers, handlers: dict) -> None:
    parser = subparsers.add_parser(
        "discover-collection-tracks",
        help="Rank collection entries for an external track list and write a review CSV",
    )
    parser.add_argument("collection", type=Path)
    parser.add_argument("tracklist", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.50)
    handlers["discover-collection-tracks"] = _handle_discover_collection_tracks
