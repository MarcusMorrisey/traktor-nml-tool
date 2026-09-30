"""Which tracked attributes an operator can answer for, and which the run
answers for them.

The six attributes splice compares two copies of one track on divide in
two. artist, title and album are EDITORIAL: two Traktor collections
disagreeing about them disagree about something a person typed, and only
a person can say which reading the merged collection should carry.
filesize, playtime_float and bitrate are MEASURED: Traktor wrote both
numbers by analysing the same file at the LOCATION the identity is
derived from (model.py:66-96), so both are real recorded facts and there
is no operator judgement to ask for. A group diverging on measured
attributes alone is settled by the winning record rather than put to the
operator (DL-325).

This is NOT matching.py's tolerant verification. That rule compares
Traktor's recorded numbers against the bytes on disk - two measurement
systems, one of which may be stale - and its tolerance answers "is this
the same file". The rule here compares Traktor against Traktor and
answers "is there a judgement to ask for". The two questions are
different, so they share no tolerance and no vocabulary: a reader
unifying the two tolerances would be unifying two different questions
(DL-325).

OUTLIER_BAND is not the rule. It was measured as one and withdrawn: on a
real collection pair the group-level survivor count plateaus past 1%
(2,203 at 1%, 2,176 at 10%), so no band separates the 2 KB filesize
drifts from the rest. It survives as the threshold above which a settled
group is worth READING - the six playtime_float groups whose gap reaches
3,516 seconds show as a wrong track length in Traktor until it
re-analyses, and the outlier listing is what names them (DL-330).

Imports nothing from traktor_nml, so splice.py, the GUI report and the
CLI all reach one definition of the partition and one band, and the
suite reads every rule here under the system interpreter (DL-069,
DL-326).
"""

from __future__ import annotations

from dataclasses import dataclass

# The order a conflict CSV's attrs column, the resolve rail and the
# outlier listing read the six names in. splice.py imports this rather
# than holding its own tuple, and answer_detail.LABELS is keyed by these
# same names (DL-326).
TRACKED_ATTRS = ("artist", "title", "album", "filesize", "playtime_float", "bitrate")

# What a person typed, and what Traktor measured. The two partition
# TRACKED_ATTRS: a name in neither would be tracked and never classified,
# which is a divergence the tier could not decide about at all.
EDITORIAL_ATTRS = ("artist", "title", "album")
MEASURED_ATTRS = ("filesize", "playtime_float", "bitrate")

# A relative gap, against the larger of the two values. 0.01 is 1%, the
# point past which the survivor curve plateaus, so a group above it
# differs by more than an encoder's rounding (DL-330).
OUTLIER_BAND = 0.01


@dataclass(frozen=True)
class OutlierReading:
    """One measured attribute a settled group diverges widely on: the
    attribute, the two ends of the spread and the gap as a fraction of
    the larger end.

    A reading, not a row to decide. It carries no candidate and no
    member reference, because nothing about it is put to the operator
    (DL-330).
    """

    attr: str
    low: str
    high: str
    relative_gap: float


def split_by_tier(attrs) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The names in attrs divided into (editorial, measured), each in
    TRACKED_ATTRS order.

    attrs is any iterable of tracked attribute names - the divergent
    names splice computes for one identity group. The two tuples answer
    the caller's two questions in one pass: whether an editorial
    judgement exists for the group, and which measured names the run
    answers for the operator instead (DL-325, DL-327).

    A name in neither tuple is dropped from both: the caller's question
    is whether an editorial judgement exists, and an unclassified name
    answers it no more than a measured one does.
    """
    given = set(attrs)
    return (
        tuple(a for a in EDITORIAL_ATTRS if a in given),
        tuple(a for a in MEASURED_ATTRS if a in given),
    )


def outlier_attrs(values_by_attr) -> tuple[OutlierReading, ...]:
    """One reading per measured attribute in values_by_attr whose spread
    exceeds OUTLIER_BAND of its larger value, in MEASURED_ATTRS order.

    values_by_attr maps a measured attribute name to the values the
    group's members hold for it. A value that does not parse as a number
    contributes nothing rather than raising: a record with no INFO
    element carries the empty string, and a page build is not the place
    a float() failure surfaces (the reason answer_detail.format_value
    returns None for the same input, ref: DL-248).

    The comparison is against the LARGER value and is strict, so a gap
    exactly at the band is not an outlier: the band is where reading
    starts, not where it is reached.

    The readings come back in MEASURED_ATTRS order rather than in the
    order values_by_attr happens to hold, so one group's listing reads
    the same way whichever attribute splice found divergent first, and
    the CLI report and the screen read one ordering from one module
    (DL-326).

    A non-positive larger value answers nothing and yields no reading:
    the band is a fraction of the larger of the two values, and a
    fraction of zero names no spread (DL-330).
    """
    readings = []
    for attr in MEASURED_ATTRS:
        raw_values = values_by_attr.get(attr) or ()
        numbers = []
        for raw in raw_values:
            try:
                numbers.append((float(raw), str(raw)))
            except (TypeError, ValueError):
                continue
        if len(numbers) < 2:
            continue
        low, high = min(numbers), max(numbers)
        if high[0] <= 0:
            continue
        gap = (high[0] - low[0]) / high[0]
        if gap > OUTLIER_BAND:
            readings.append(OutlierReading(attr, low[1], high[1], gap))
    return tuple(readings)
