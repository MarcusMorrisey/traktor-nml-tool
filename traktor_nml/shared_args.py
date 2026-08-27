"""Confidence and refutation semantics shared below the commands/ layer.

resolve_confidence, should_refute and refutation_disabled_line are pure
functions of an argparse.Namespace with no argparse registration or
stream dependency of their own. reconnect_run.py and reconnect_render.py
import them from here rather than from commands/_shared_args.py, because
commands/ imports downward into reconnect_run.py and reconnect_render.py
and never the reverse - a core or renderer module importing from
commands/ would create the cycle that direction forbids.
commands/_shared_args.py imports these same three names from here, so
every existing importer of them (compare_cmd.py, reconnect_cmd.py) keeps
working unchanged.
"""

from __future__ import annotations

import argparse
from typing import Optional

from .confidence import MatchConfidence, parse_match_confidence


def resolve_confidence(args: argparse.Namespace) -> MatchConfidence:
    """Resolve the effective MatchConfidence: an explicit
    --match-confidence always wins; otherwise --allow-artist-title-only
    selects loose and its absence selects strict (DL-010)."""
    if getattr(args, "match_confidence", None):
        return parse_match_confidence(args.match_confidence)
    return MatchConfidence.from_legacy_flag(args.allow_artist_title_only)


def should_refute(args: argparse.Namespace) -> bool:
    """Whether the cascade should apply the size/duration check.

    Pure: safe to call anywhere, any number of times. The warning is a
    separate call precisely so this one carries no call-once contract -
    reading a flag and announcing it are different jobs, and conflating
    them meant a caller with two passes over the same run had to know to
    cache the result or the warning printed twice.
    """
    return not getattr(args, "no_refute", False)


def refutation_disabled_line(args: argparse.Namespace) -> Optional[str]:
    """The refutation-disabled message text, or None when refutation is
    still active. warn_refutation_disabled and reconnect_render both read
    this so the literal has one definition: no manifest case sets
    --no-refute for either reconnect command, so a second copy of the
    text would drift invisibly.
    """
    # should_refute is the single source of truth for the flag reading;
    # this function only decides the message text, so the two never
    # disagree about whether refutation is active.
    if should_refute(args):
        return None
    return (
        "refutation_disabled=size and duration contradictions will be ignored; "
        "a candidate the collection's own FILESIZE/PLAYTIME_FLOAT contradict can now win a match"
    )
