"""Turns a RecordReview plus one operator decision into the row Specs
renders, with no framework import.

Two axes are kept apart throughout this module: status is what the
matcher (and resolve_reconnection's destination-collision overlay)
found, decision is what the operator has said about it. row_status
folds both into the six statuses Specs names - matched, ambiguous,
refuted, format, rejected and no_match - and returns nothing outside
that set. A left-missing decision wins outright and yields rejected; an
accepted decision yields no status of its own and leaves the
matcher-derived status standing, so a Strong match the operator has
audited still reads matched and stays rejectable afterwards. Accepted is
therefore a wizard_state decision state, never a row_status return, and
the Accepted chip of FILTERS selects on the decision axis rather than on
status - which is also why FILTERS holds seven entries against six
statuses rather than mapping one to one.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Callable, Iterable, Optional

from ..review import CandidateView, RecordReview

# The three decision states wizard_state.py assigns, named here too so
# row_status and FILTERS can be checked against them without importing
# wizard_state (which would invert the dependency this module's own
# docstring describes: review_model derives a row from a decision,
# wizard_state derives the amended mapping from the same decision).
UNDECIDED = "undecided"
ACCEPTED = "accepted"
LEFT_MISSING = "left_missing"

# The six statuses Specs names, matched is not accepted.
STATUSES = frozenset({"matched", "ambiguous", "refuted", "format", "rejected", "no_match"})


def row_status(review: RecordReview, decision_state: str) -> str:
    """One of the six statuses in STATUSES, never any other token -
    in particular never the literal "accepted", which is a decision
    state and not a status this function returns.
    """
    if decision_state == LEFT_MISSING:
        return "rejected"
    if review.status == "matched":
        winner = review.chosen
        if winner is not None and _suffix(winner.file_name) != _suffix(review.old.file_name):
            return "format"
        return "matched"
    if review.status in ("ambiguous", "destination_collision"):
        return "ambiguous"
    if review.status == "refuted":
        return "refuted"
    return "no_match"


def _suffix(file_name: str) -> str:
    return PurePosixPath(file_name).suffix.lower()


# The tier table this module owns rather than matching.py: both the
# strength grouping and the format/matched suffix comparison above are
# questions about how a match is described to the operator, not about
# which match was made.
_STRONG_TIERS = frozenset({
    "audio_id", "artist_title_size_time", "artist_title_file", "file_size_time",
})
_GOOD_TIERS = frozenset({
    "artist_title_album_time", "path_suffix_3",
})


def display_confidence(candidate: Optional[CandidateView]) -> str:
    """Strong, Good, Weak or None, per Specs' four confidence levels.

    audio_id and the three artist-title-plus-field tiers (size+time,
    file, and the field-agreement tier that keys on file size and
    duration alone) read Strong; artist_title_album_time and the deep
    path-suffix tier read Good; every other cascade tier - the shallow
    path suffixes, the container-stripped name tiers, plain artist_title
    and a fingerprint-provider tier alike - reads Weak; the absence of a
    candidate reads None.
    """
    if candidate is None:
        return "None"
    if candidate.key_name in _STRONG_TIERS:
        return "Strong"
    if candidate.key_name in _GOOD_TIERS:
        return "Good"
    return "Weak"


FilterPredicate = Callable[[str, str], bool]

# Specs' seven filter chips, in the order Specs lists them, each paired
# with the predicate it selects rows on: (status, decision_state) -> bool.
# The first four - ambiguous, refuted, format, no_match - are the queue:
# the four statuses a row can carry that neither reads as done (matched)
# nor is a decision the operator has already made (accepted, rejected).
FILTERS: tuple[tuple[str, str, FilterPredicate], ...] = (
    ("ambiguous", "Needs review", lambda status, decision: status == "ambiguous"),
    ("refuted", "Refuted", lambda status, decision: status == "refuted"),
    ("format", "Re-encoded", lambda status, decision: status == "format"),
    ("no_match", "Not found", lambda status, decision: status == "no_match"),
    ("accepted", "Accepted", lambda status, decision: decision == ACCEPTED),
    ("rejected", "Rejected", lambda status, decision: status == "rejected"),
    ("matched", "Found automatically", lambda status, decision: status == "matched"),
)

QUEUE_FILTER_KEYS: tuple[str, ...] = tuple(key for key, _label, _pred in FILTERS[:4])


def filter_counts(rows: Iterable[tuple[str, str]]) -> dict[str, int]:
    """Count every row - each a (status, decision_state) pair, as
    row_status and a wizard_state decision_state produce - against each
    of the seven FILTERS predicates.
    """
    rows = list(rows)
    counts: dict[str, int] = {key: 0 for key, _label, _pred in FILTERS}
    for status, decision in rows:
        for key, _label, predicate in FILTERS:
            if predicate(status, decision):
                counts[key] += 1
    return counts
