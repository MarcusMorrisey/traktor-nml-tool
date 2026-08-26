"""preview-compare, scan-compare-candidates and rewrite-from-collection-compare."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..confidence import MatchConfidence, parse_match_confidence
from ..matching import build_new_indexes, match_records
from ..model import collection_records
from ..reconnect import enforce_one_to_one
from ..rewrite import (
    _collect_compare_patches,
    add_no_refute_argument,
    read_and_parse_source,
    rewrite_from_collection_compare,
    warn_if_refutation_disabled,
    write_nml_safely,
)
from ..xmlio import XML_PARSE_ERROR, parse_xml


def add_confidence_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--match-confidence",
        choices=[level.value for level in MatchConfidence],
        default=None,
        help="Match cascade confidence ladder (default: strict, or loose if "
        "--allow-artist-title-only is given).",
    )
    parser.add_argument(
        "--allow-artist-title-only",
        action="store_true",
        help="Deprecated alias for --match-confidence loose.",
    )


def resolve_confidence(args: argparse.Namespace) -> MatchConfidence:
    """Resolve the effective MatchConfidence: an explicit
    --match-confidence always wins; otherwise --allow-artist-title-only
    selects loose and its absence selects strict (DL-010)."""
    if getattr(args, "match_confidence", None):
        return parse_match_confidence(args.match_confidence)
    return MatchConfidence.from_legacy_flag(args.allow_artist_title_only)


def preview_compare_nml(
    old_root, new_root, limit: int, confidence: MatchConfidence, refute: bool = True
) -> int:
    old_records = collection_records(old_root)
    new_records = collection_records(new_root)
    mapping, stats, samples = match_records(old_records, new_records, confidence, refute=refute)

    print(f"old_collection_entries={len(old_records)}")
    print(f"new_collection_entries={len(new_records)}")
    for key, value in stats.items():
        print(f"{key}={value}")
    print(f"primarykey_updates_available={len(mapping)}")

    if samples:
        print("sample_matches:")
        for label, before, after, matched_by in samples[:limit]:
            print(f"- {label}")
            print(f"  matched_by={matched_by}")
            print(f"  before={before}")
            print(f"  after={after}")

    return 0


def compare_stats_dict(
    old_root, new_root, confidence: MatchConfidence, refute: bool = True
) -> tuple[dict[str, int], list[tuple[str, str, str, str]]]:
    old_records = collection_records(old_root)
    new_records = collection_records(new_root)
    mapping, stats, samples = match_records(old_records, new_records, confidence, refute=refute)
    stats = {
        "old_collection_entries": len(old_records),
        "new_collection_entries": len(new_records),
        **stats,
        "primarykey_updates_available": len(mapping),
    }
    return stats, samples


def scan_compare_candidates(
    target_path: Path, candidates_dir: Path, limit: int, confidence: MatchConfidence,
    refute: bool = True,
) -> int:
    try:
        target_root = parse_xml(target_path).getroot()
    except FileNotFoundError:
        print(f"input_not_found={target_path.as_posix()}", file=sys.stderr)
        return 2
    except XML_PARSE_ERROR as exc:
        print(f"xml_parse_error={target_path.as_posix()}: {exc}", file=sys.stderr)
        return 2

    candidates = sorted(candidates_dir.glob("**/*.nml"))
    if not candidates:
        print(f"no_candidates_found={candidates_dir}")
        return 0

    rows: list[dict[str, object]] = []
    for candidate in candidates:
        try:
            candidate_root = parse_xml(candidate).getroot()
        except (XML_PARSE_ERROR, FileNotFoundError):
            continue

        stats, _samples = compare_stats_dict(candidate_root, target_root, confidence, refute=refute)
        old_entries = int(stats["old_collection_entries"])
        matched = int(stats["matched"])
        ambiguous = int(stats["ambiguous"])
        unmatched = int(stats["unmatched"])
        ratio = 0.0 if old_entries == 0 else matched / old_entries
        rows.append(
            {
                "path": candidate,
                "matched": matched,
                "ratio": ratio,
                "ambiguous": ambiguous,
                "unmatched": unmatched,
                "matched_audio_id": int(stats["matched_audio_id"]),
                "matched_artist_title_size_time": int(stats["matched_artist_title_size_time"]),
                "matched_artist_title_file": int(stats["matched_artist_title_file"]),
                "matched_file_size_time": int(stats["matched_file_size_time"]),
                "matched_artist_title_album_time": int(stats["matched_artist_title_album_time"]),
                "matched_artist_title": int(stats["matched_artist_title"]),
                "old_entries": old_entries,
            }
        )

    rows.sort(key=lambda row: (row["matched"], row["ratio"], -row["ambiguous"]), reverse=True)

    print(f"target={target_path.as_posix()}")
    print(f"candidates_scanned={len(rows)}")
    print("top_candidates:")
    for row in rows[:limit]:
        print(
            f"- path={row['path'].as_posix()}"
            f" matched={row['matched']}"
            f" ratio={row['ratio']:.4f}"
            f" ambiguous={row['ambiguous']}"
            f" unmatched={row['unmatched']}"
            f" audio_id={row['matched_audio_id']}"
            f" title_size_time={row['matched_artist_title_size_time']}"
            f" title_file={row['matched_artist_title_file']}"
            f" file_size_time={row['matched_file_size_time']}"
            f" album_time={row['matched_artist_title_album_time']}"
            f" title_only={row['matched_artist_title']}"
        )

    return 0


def _parse_input_or_none(path: Path) -> tuple[object, int | None]:
    """Parse path, returning (tree, None) on success or (None, exit_code)
    with the diagnostic already printed to stderr on failure - split per
    path (rather than one try/except around both old_input and new_input)
    so the printed error names the specific file that actually failed."""
    try:
        return parse_xml(path), None
    except FileNotFoundError:
        print(f"input_not_found={path.as_posix()}", file=sys.stderr)
        return None, 2
    except XML_PARSE_ERROR as exc:
        print(f"xml_parse_error={path.as_posix()}: {exc}", file=sys.stderr)
        return None, 2


def _handle_preview_compare(args: argparse.Namespace) -> int:
    old_tree, error_code = _parse_input_or_none(args.old_input)
    if error_code is not None:
        return error_code
    new_tree, error_code = _parse_input_or_none(args.new_input)
    if error_code is not None:
        return error_code
    return preview_compare_nml(
        old_tree.getroot(), new_tree.getroot(), limit=args.limit,
        confidence=resolve_confidence(args),
        refute=warn_if_refutation_disabled(args),
    )


def _handle_scan_compare_candidates(args: argparse.Namespace) -> int:
    return scan_compare_candidates(
        target_path=args.target_input,
        candidates_dir=args.candidates_dir,
        limit=args.limit,
        confidence=resolve_confidence(args),
        refute=warn_if_refutation_disabled(args),
    )


def _handle_rewrite_from_collection_compare(args: argparse.Namespace) -> int:
    confidence = resolve_confidence(args)
    # Read once here, not inside the closures below: this command runs
    # _collect_patches and mutate_tree over the same invocation, and the
    # warning must print once for the run rather than once per pass.
    refute = warn_if_refutation_disabled(args)

    # Parsed once, upfront, with the same xml_parse_error/input_not_found
    # handling old_input gets inside write_nml_safely - previously each
    # closure below re-parsed new_input itself with no error handling at
    # all, so a malformed new_input crashed with an unhandled exception
    # instead of the documented diagnostic + exit 2.
    new_result = read_and_parse_source(args.new_input)
    if new_result.error is not None:
        print(new_result.error, file=sys.stderr)
        return 2
    new_root = new_result.root

    def _collect_patches(old_root):
        old_records = collection_records(old_root)
        new_records = collection_records(new_root)
        indexes = build_new_indexes(new_records, confidence)
        mapping, match_stats, samples = match_records(
            old_records, new_records, confidence, indexes=indexes, refute=refute
        )
        mapping, match_stats, _collided = enforce_one_to_one(
            mapping, match_stats, old_records, indexes, confidence
        )
        patches, apply_stats = _collect_compare_patches(old_root, old_records, mapping)
        return patches, {**apply_stats, **match_stats}, samples

    def mutate_tree(old_root, dry_run):
        stats, samples = rewrite_from_collection_compare(
            old_root, new_root, dry_run=dry_run, confidence=confidence, refute=refute
        )
        return stats, samples

    return write_nml_safely(
        args.old_input, args.output, args.dry_run, _collect_patches, mutate_tree,
        extra_inputs=(args.new_input,),
    )


def register(subparsers, handlers: dict) -> None:
    compare_preview_parser = subparsers.add_parser(
        "preview-compare", help="Preview old-vs-new collection matching without writing"
    )
    compare_preview_parser.add_argument("old_input", type=Path)
    compare_preview_parser.add_argument("new_input", type=Path)
    compare_preview_parser.add_argument("--limit", type=int, default=10)
    add_no_refute_argument(compare_preview_parser)
    add_confidence_args(compare_preview_parser)
    handlers["preview-compare"] = _handle_preview_compare

    scan_parser = subparsers.add_parser(
        "scan-compare-candidates",
        help="Scan a folder of backup collections and rank likely matches against a target collection",
    )
    scan_parser.add_argument("target_input", type=Path)
    scan_parser.add_argument("candidates_dir", type=Path)
    scan_parser.add_argument("--limit", type=int, default=10)
    add_no_refute_argument(scan_parser)
    add_confidence_args(scan_parser)
    handlers["scan-compare-candidates"] = _handle_scan_compare_candidates

    compare_rewrite_parser = subparsers.add_parser(
        "rewrite-from-collection-compare",
        help="Update an old NML's locations and PRIMARYKEYs using a newer collection file",
    )
    compare_rewrite_parser.add_argument("old_input", type=Path)
    compare_rewrite_parser.add_argument("new_input", type=Path)
    compare_rewrite_parser.add_argument("output", type=Path)
    compare_rewrite_parser.add_argument("--dry-run", action="store_true", help="Skip the write to the NML output file. Any report or CSV side file this command writes is still written.")
    add_no_refute_argument(compare_rewrite_parser)
    add_confidence_args(compare_rewrite_parser)
    handlers["rewrite-from-collection-compare"] = _handle_rewrite_from_collection_compare
