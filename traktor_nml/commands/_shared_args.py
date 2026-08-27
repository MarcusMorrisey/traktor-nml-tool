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
# Re-exported from shared_args.py: reconnect_run.py and reconnect_render.py
# also need resolve_confidence/should_refute/refutation_disabled_line, and
# commands/ is the only side of that import boundary allowed to depend on
# the other (ref: DL-052). compare_cmd.py and reconnect_cmd.py import these
# three names from this module rather than from shared_args.py directly.
from ..shared_args import refutation_disabled_line, resolve_confidence, should_refute


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


def add_no_refute_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-refute",
        action="store_true",
        help="Do not drop candidates whose size or duration contradicts the collection entry. "
        "The tolerances are calibrated against one real library; use this if they are rejecting "
        "files you know are correct (a run reports how many it withdrew as refuted=N).",
    )


def warn_refutation_disabled(args: argparse.Namespace) -> None:
    """Announce --no-refute once per run, if it is set.

    A run that ignores size and duration contradictions can commit a
    rewrite onto a file the collection's own numbers say is the wrong one,
    so the switch says so on every run rather than only in --help.
    """
    line = refutation_disabled_line(args)
    if line is not None:
        print(line, file=sys.stderr)
