"""scan-reconnect-candidates and rewrite-from-reconnect subcommands."""

from __future__ import annotations

import argparse
from pathlib import Path

from .. import reconnect_run
from ..reconnect_render import emit, render_rewrite_from_reconnect, render_scan_reconnect_candidates
from ._shared_args import add_confidence_args, add_no_refute_argument

try:
    # See reconnect_run.py's own defensive import: --fpcalc-timeout's
    # default needs FPCALC_TIMEOUT_SECONDS whether or not fingerprint.py
    # (the M-005 acoustic-fingerprint tier) is present yet.
    from ..fingerprint import FPCALC_TIMEOUT_SECONDS
except ImportError:  # pragma: no cover - fingerprint tier lands in M-005
    FPCALC_TIMEOUT_SECONDS = 30.0


def add_reconnect_args(parser: argparse.ArgumentParser) -> None:
    add_no_refute_argument(parser)
    parser.add_argument(
        "--fpcalc-timeout",
        type=float,
        default=FPCALC_TIMEOUT_SECONDS,
        help=f"Seconds to allow one file's fingerprint before giving up on it "
        f"(default {FPCALC_TIMEOUT_SECONDS:g}). The file is counted as "
        f"fingerprint_timeout and the scan continues, so one pathological "
        f"file cannot stall a long run.",
    )
    parser.add_argument(
        "--scan-root",
        type=Path,
        action="append",
        dest="scan_roots",
        required=True,
        help="Filesystem root to scan for candidate audio files (repeatable).",
    )
    parser.add_argument(
        "--volume-map",
        nargs=3,
        action="append",
        metavar=("SCAN_ROOT", "VOLUME", "VOLUMEID"),
        help="Explicit VOLUME/VOLUMEID for a scan root (repeatable); required when the "
        "prefix scan of the old collection cannot resolve a single unambiguous pair.",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path(".traktor_nml_tagcache.json"),
        help="Disk-scan tag cache path. Written/updated as scan roots are indexed, "
        "independently of --dry-run: --dry-run only suppresses writes to the output "
        "NML, not this cache file.",
    )
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--csv", type=Path)
    parser.add_argument(
        "--fingerprint",
        action="store_true",
        help="Enable the acoustic-fingerprint match tier (requires pyacoustid, the fpcalc binary, and the chromaprint shared library); "
        "opt-in and off by default since these are optional dependencies.",
    )
    add_confidence_args(parser)


def _handle_scan_reconnect_candidates(args: argparse.Namespace) -> int:
    """Argparse wiring only: emit(render(core(args))). Holds no print
    call and writes to neither stream itself - the command layer never
    computes a value it prints."""
    return emit(render_scan_reconnect_candidates(reconnect_run.scan_reconnect_candidates(args), args))


def _handle_rewrite_from_reconnect(args: argparse.Namespace) -> int:
    """Argparse wiring only: emit(render(core(args))), same shape as
    _handle_scan_reconnect_candidates above and covered by the same
    printless guard."""
    return emit(render_rewrite_from_reconnect(reconnect_run.rewrite_from_reconnect(args), args))


def register(subparsers, handlers: dict) -> None:
    scan_parser = subparsers.add_parser(
        "scan-reconnect-candidates",
        help="Match an old collection's tracks against disk-scan candidates without writing",
    )
    scan_parser.add_argument("old_input", type=Path)
    add_reconnect_args(scan_parser)
    handlers["scan-reconnect-candidates"] = _handle_scan_reconnect_candidates

    rewrite_parser = subparsers.add_parser(
        "rewrite-from-reconnect",
        help="Rewrite an old collection's LOCATIONs and PRIMARYKEYs from a disk scan",
    )
    rewrite_parser.add_argument("old_input", type=Path)
    rewrite_parser.add_argument("output", type=Path)
    rewrite_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stats without writing the output NML. Note: the --cache tag cache "
        "and the --csv ambiguity report are still written, since neither is the "
        "command's declared output - the cache is a scan speed-up and the report "
        "is a record of what the run saw.",
    )
    add_reconnect_args(rewrite_parser)
    handlers["rewrite-from-reconnect"] = _handle_rewrite_from_reconnect
