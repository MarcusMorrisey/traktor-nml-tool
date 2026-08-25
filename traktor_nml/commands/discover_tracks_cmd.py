"""Discover possible audio files for an external track list without writing NML."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

from ..discovery import rank_candidates
from ..diskscan import index_scan_roots
from ..rewrite import path_collides, write_bytes_atomically
from ..tagcache import TagCache
from ..tracklist import parse_tracklist


def _report_bytes(matches) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "line_number",
            "requested_artist",
            "requested_title",
            "candidate_path",
            "candidate_artist",
            "candidate_title",
            "source",
            "score",
            "artist_score",
            "title_score",
        ],
    )
    writer.writeheader()
    for match in matches:
        writer.writerow(
            {
                "line_number": match.line.line_number,
                "requested_artist": match.line.artist,
                "requested_title": match.line.title,
                "candidate_path": "" if match.candidate_path is None else str(match.candidate_path),
                "candidate_artist": match.candidate_artist,
                "candidate_title": match.candidate_title,
                "source": match.source,
                "score": f"{match.score:.3f}",
                "artist_score": f"{match.artist_score:.3f}",
                "title_score": f"{match.title_score:.3f}",
            }
        )
    return output.getvalue().encode("utf-8")


def _handle_discover_tracks(args: argparse.Namespace) -> int:
    if path_collides(args.output, args.tracklist):
        print("output_must_differ_from_input", file=sys.stderr)
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
    cache = TagCache(args.cache)
    scan_stats: dict[str, int] = {}
    candidates = index_scan_roots(args.scan_roots, cache, refresh_cache=args.refresh_cache, stats=scan_stats)
    matches = rank_candidates(lines, candidates, max_candidates=args.max_candidates, min_score=args.min_score)

    for key, value in scan_stats.items():
        print(f"{key}={value}")
    print(f"lines_read={len(lines) + len(unparseable)}")
    print(f"unparseable_lines={len(unparseable)}")
    print(f"candidates_scanned={len(candidates)}")
    print(f"review_candidates={sum(match.candidate_path is not None for match in matches)}")
    print(f"no_candidate_rows={sum(match.candidate_path is None for match in matches)}")
    try:
        write_bytes_atomically(args.output, _report_bytes(matches))
    except OSError as exc:
        print(f"output_write_error={exc}", file=sys.stderr)
        return 2
    print(f"report_written={args.output}")
    return 0


def register(subparsers, handlers: dict) -> None:
    parser = subparsers.add_parser(
        "discover-tracks",
        help="Rank disk files for an external track list and write a review CSV",
    )
    parser.add_argument("tracklist", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scan-root", type=Path, action="append", dest="scan_roots", required=True)
    parser.add_argument("--cache", type=Path, default=Path(".traktor_nml_tagcache.json"))
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.50)
    handlers["discover-tracks"] = _handle_discover_tracks
