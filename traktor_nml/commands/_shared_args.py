"""Command-line arguments shared by more than one subcommand.

Two subcommand families - compare and reconnect - drive the same match
cascade and therefore need the same knobs. Registering those flags here
rather than in whichever module happened to need them first keeps one home
for the pattern: a third shared flag has one precedent to copy instead of
two, and a core module does not end up owning argparse and stderr concerns
that belong to the CLI surface.
"""

from __future__ import annotations

import argparse
import sys

from ..confidence import MatchConfidence, parse_match_confidence


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


def add_no_refute_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-refute",
        action="store_true",
        help="Do not drop candidates whose size or duration contradicts the collection entry. "
        "The tolerances are calibrated against one real library; use this if they are rejecting "
        "files you know are correct (a run reports how many it withdrew as refuted=N).",
    )


def should_refute(args: argparse.Namespace) -> bool:
    """Whether the cascade should apply the size/duration check.

    Pure: safe to call anywhere, any number of times. The warning is a
    separate call precisely so this one carries no call-once contract -
    reading a flag and announcing it are different jobs, and conflating
    them meant a caller with two passes over the same run had to know to
    cache the result or the warning printed twice.
    """
    return not getattr(args, "no_refute", False)


def warn_refutation_disabled(args: argparse.Namespace) -> None:
    """Announce --no-refute once per run, if it is set.

    A run that ignores size and duration contradictions can commit a
    rewrite onto a file the collection's own numbers say is the wrong one,
    so the switch says so on every run rather than only in --help.
    """
    if not should_refute(args):
        print(
            "refutation_disabled=size and duration contradictions will be ignored; "
            "a candidate the collection's own FILESIZE/PLAYTIME_FLOAT contradict can now win a match",
            file=sys.stderr,
        )
