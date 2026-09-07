"""The reconstruct page's step table and the rail records it renders,
with no framework import.

STEPS is the one place a step number or a step label is written:
`Reconstruct.dc.html`, `Preview.dc.html`, `Resolve.dc.html` and
`Write.dc.html` draw one rail of four steps and each names its own row,
so the four artboards agree on the order and this table carries it.
rail_records(current) derives one record per row in that same order,
carrying the row's number and label plus the three things a rail entry
renders with - whether it reads done, current or upcoming, the class
string it carries, and its aria-current value.

Two axes are kept apart here, the way navigation.py keeps the section
table apart from the active route: the table is what the rail holds, and
the step the page is showing is what the operator has walked to.
Position is the single point where they meet - a row before the current
one reads done, the row equal to it reads current, and a row after it
reads upcoming, exactly one current at a time, and a current number
matching no row leaves every row upcoming rather than falling back to
the first (DL-202).

reachable() is the second rule and is separate from the first on
purpose: a rail says where the operator is, and reachability says where
they may go. The resolve step's gate is conflict_model.resolve_gate's
own answer, so the rule that shuts the write step and the sentence the
footer prints read one value (DL-204).

Every rule here is a pure computation over integers and strings, so a
guard runs it on an interpreter with no framework present (DL-203).
"""

from __future__ import annotations

from dataclasses import dataclass

# The four step numbers, named so a call site names a step rather than a
# digit. The numbers are the rail's own, counted from one, because the
# rail renders them.
SET_UP = 1
PREVIEW = 2
RESOLVE = 3
WRITE = 4

# The ordered step table: number first, label second. Every other module
# names a step or a label by reading this table.
STEPS: tuple[tuple[int, str], ...] = (
    (SET_UP, "Set up"),
    (PREVIEW, "Preview"),
    (RESOLVE, "Resolve"),
    (WRITE, "Write"),
)

# The three positions a rail entry reads, as tokens rather than as
# booleans: a done row and an upcoming row differ in what has happened
# to them, not in a single flag's polarity.
DONE = "done"
CURRENT = "current"
UPCOMING = "upcoming"

# The class every rail entry carries, and the second class a done or a
# current entry carries alongside it. The three name theme.py's own
# ".wizard-step", ".wizard-step-done" and ".wizard-step-current" rules;
# this module writes the names and theme.py holds the values behind them
# (DL-069, DL-188).
STEP_CLASS = "wizard-step"
STEP_DONE_CLASS = "wizard-step-done"
STEP_CURRENT_CLASS = "wizard-step-current"

# The class the marker inside every entry carries, and the second class
# the current entry's marker carries alongside it. The current marker is
# its own class rather than a rule descending from STEP_CURRENT_CLASS,
# because its ink is read against the ground the marker paints rather
# than against the ground of the entry around it.
MARKER_CLASS = "wizard-step-number"
MARKER_CURRENT_CLASS = "wizard-step-number-current"

# The aria-current value the current entry reads, and the value the rest
# read: None, which is the absence of the attribute rather than an empty
# string. "step" rather than "page", which is what Resolve.dc.html:124
# carries on the entry it draws as current.
ARIA_CURRENT_STEP = "step"

# What a done entry renders in its marker in place of its number: the
# check mark Resolve.dc.html:122-123 draws on the two steps behind the
# current one. Written as an escape rather than as the glyph, so this
# module stays ASCII on disk and a tool reading it under a codepage
# that has no U+2713 reads it at all.
DONE_MARKER = "\u2713"


@dataclass(frozen=True)
class RailRecord:
    """One rendered rail entry: the row's number and label, the position
    it reads, the class string it renders with, the text its marker
    carries, and its aria-current value or None."""

    number: int
    label: str
    state: str
    classes: str
    marker: str
    marker_classes: str
    aria_current: str | None


def rail_records(current: int) -> tuple[RailRecord, ...]:
    """One record per STEPS row in table order.

    The record whose number equals current reads CURRENT and carries
    both STEP_CLASS and STEP_CURRENT_CLASS at aria-current
    ARIA_CURRENT_STEP; a record before it reads DONE and carries
    STEP_CLASS and STEP_DONE_CLASS at aria-current None; a record after
    it reads UPCOMING and carries STEP_CLASS alone. A current equal to
    no row's number leaves every record UPCOMING, so a caller holding a
    number the table does not name renders a rail with nothing marked
    rather than a rail marking the first row by accident.
    """
    return tuple(_record(number, label, current) for number, label in STEPS)


def _record(number: int, label: str, current: int) -> RailRecord:
    """One row's record, read from its position against `current`.

    DONE is guarded on `current` naming a row of its own, so a number
    the table does not carry leaves the rows after it UPCOMING rather
    than reading every row done. The marker is the check mark for a done
    row and the row's own number otherwise, which is what
    Resolve.dc.html:122-123 draws on the two steps behind the current
    one and :124 on the current one.
    """
    if number == current:
        state = CURRENT
    elif any(row == current for row, _ in STEPS) and number < current:
        state = DONE
    else:
        state = UPCOMING
    return RailRecord(
        number=number,
        label=label,
        state=state,
        classes=_classes(state),
        marker=DONE_MARKER if state == DONE else str(number),
        marker_classes=(
            f"{MARKER_CLASS} {MARKER_CURRENT_CLASS}"
            if state == CURRENT
            else MARKER_CLASS
        ),
        aria_current=ARIA_CURRENT_STEP if state == CURRENT else None,
    )


def _classes(state: str) -> str:
    """The class string one entry carries for its position.

    STEP_CLASS is on every entry and a done or a current entry carries
    its state class beside it. Which of the two paints is theme.py's
    to settle - it declares the state rules after .wizard-step, so they
    win at equal specificity - and this module writes names alone
    (DL-069).
    """
    if state == CURRENT:
        return f"{STEP_CLASS} {STEP_CURRENT_CLASS}"
    if state == DONE:
        return f"{STEP_CLASS} {STEP_DONE_CLASS}"
    return STEP_CLASS


def reachable(
    target: int, has_result: bool, has_output: bool, all_decided: bool
) -> bool:
    """Whether the page may show `target`.

    SET_UP is always reachable: it is where the collections are named
    and a run is discarded whenever one of them changes, so an operator
    walking back to it is walking to the controls that fix whatever
    stopped them.

    PREVIEW and RESOLVE need a held run. The preview is the run - the
    page calls assemble_output with dry_run and holds what it returned -
    so a resolve step without one would offer answers over groups no run
    reported (DL-107).

    WRITE needs a run that produced an output, and whose divergences are
    every one decided. has_output rather than has_result, because a run
    that refused is a held result carrying no output: the write step
    reports what the new file will hold, and a refused run holds nothing
    to report - it stood there printing zeros for the playlists filled
    and the tracks the file holds beside a count of answers read off the
    decisions, which is the step describing a file that was never
    assembled (DL-224). all_decided is conflict_model.resolve_gate's own
    answer, so the step this refuses and the count the footer prints
    cannot disagree (DL-204). A run that reported no divergence at all
    reads all_decided True and passes straight through, which is the same
    answer the gate gives for an empty group set.

    A target no STEPS row names is refused rather than defaulted, so a
    caller holding a number the table does not carry stays where it is.
    """
    if not any(number == target for number, _ in STEPS):
        return False
    if target == SET_UP:
        return True
    if target in (PREVIEW, RESOLVE):
        return has_result
    return has_output and all_decided
