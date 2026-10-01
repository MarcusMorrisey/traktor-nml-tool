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

That reasoning covers one case and one only: one file, described twice,
each collection carrying its own analysis of it. Every precondition the
case names is a precondition of the rule, and the caller checks each of
them before settling anything - the members name the one LOCATION, the
group holds the base record whose values the output keeps, and every
value the disagreement is made of is a number that can be read. Where
one of them fails the reasoning says nothing about the group, so the
group is a conflict the operator answers. unreadable_measured is the
half of that checking this module owns: a measured attribute where any
member's value is empty or unparseable holds one measurement and one
absence rather than two measurements, and a rule about two analyses of
one file has no answer for it.

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

import math
from dataclasses import dataclass
from fractions import Fraction

# The order a conflict CSV's attrs column, the resolve rail and the
# outlier listing read the six names in. splice.py imports this rather
# than holding its own tuple, and answer_detail.LABELS is keyed by these
# same names (DL-326).
TRACKED_ATTRS = ("artist", "title", "album", "filesize", "playtime_float", "bitrate")

# What a person typed, and what Traktor measured. MEASURED_ATTRS is the
# closed list of names a rule can answer for; EDITORIAL_ATTRS names the
# three the tier states as the operator's. A guard asserts the two
# partition TRACKED_ATTRS rather than split_by_tier relying on it: a name
# outside MEASURED_ATTRS reads as editorial there, so a tracked
# attribute added and classified nowhere is put to the operator rather
# than settled in silence.
EDITORIAL_ATTRS = ("artist", "title", "album")
MEASURED_ATTRS = ("filesize", "playtime_float", "bitrate")

# A relative gap, against the larger of the two values. 0.01 is 1%, the
# point past which the survivor curve plateaus, so a group above it
# differs by more than an encoder's rounding (DL-330).
OUTLIER_BAND = 0.01

# The same band as an exact rational, which is what the comparison is
# made against. 0.01 has no exact binary float, and a decimal attribute's
# gap computed in floats lands either side of the float 0.01 by an ULP:
# playtime_float 59.4 against 60.0 is exactly 1% and divides to
# 0.010000000000000024. The band is a decimal figure and a gap between
# two decimal strings is an exact rational, so the boundary is decided
# where both are exact, and OUTLIER_BAND stays the float the band is
# written and displayed as.
_OUTLIER_BAND_EXACT = Fraction(str(OUTLIER_BAND))


@dataclass(frozen=True)
class OutlierReading:
    """One measured attribute a settled group diverges widely on: the
    attribute, the value the output keeps, the member value it is read
    against, and the gap between the two as a fraction of the larger.

    kept is the winning record's own value - the number the merged
    collection will carry - and other is the member value furthest from
    it. Both are values a record in the group holds, and one of them is
    the value the output holds, so a group of three members cannot name
    a spread the merged file stands outside of.

    low and high read those same two values in magnitude order, for a
    surface stating the spread rather than the survivor.

    A reading, not a row to decide. It carries no candidate and no
    member reference, because nothing about it is put to the operator
    (DL-330).
    """

    attr: str
    kept: str
    other: str
    relative_gap: float

    @property
    def low(self) -> str:
        """The smaller of kept and other, spelled as the file spells it."""
        return min((self.kept, self.other), key=measured_number)

    @property
    def high(self) -> str:
        """The larger of kept and other, spelled as the file spells it."""
        return max((self.kept, self.other), key=measured_number)


def measured_number(raw) -> float | None:
    """The finite number raw spells, or None where raw spells none.

    float() accepts 'nan', 'inf', '-inf' and an overflowing literal such
    as '1e400', none of which is a measurement Traktor wrote: an
    infinite gap passes any band, and a NaN answers False to every
    comparison it takes part in, which makes min() and max() over a list
    holding one answer whatever the list order makes them answer. They
    are screened here, where the value is parsed, so no rule downstream
    carries a second guard for them.

    The empty string a record with no INFO element holds answers None
    the same way, which is what unreadable_measured reads.
    """
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _exact(raw, number: float) -> Fraction:
    """raw as an exact rational, read off the decimal string the file
    holds rather than off the double it parsed to.

    The string is what the collection says, and 59.4 as a double is not
    59.4, so a gap taken from the doubles cannot land on the band even
    where the decimals do. number is the fallback for a spelling float()
    accepts and Fraction does not, and it is exact for the double it is.
    """
    try:
        return Fraction(str(raw).strip())
    except (ValueError, ZeroDivisionError):
        return Fraction(number)


def split_by_tier(attrs) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The names in attrs divided into (editorial, measured), each in
    TRACKED_ATTRS order.

    attrs is any iterable of tracked attribute names - the divergent
    names splice computes for one identity group. The two tuples answer
    the caller's two questions in one pass: whether an editorial
    judgement exists for the group, and which measured names the run
    answers for the operator instead (DL-325, DL-327).

    MEASURED_ATTRS is the closed list and every other name answers the
    editorial half: a name in TRACKED_ATTRS that no tier tuple mentions
    is something no rule can answer, which is what the editorial half
    means. Dropping it from both halves is what fails open - the caller
    settles a group on an empty editorial half, so a tracked attribute
    added and classified nowhere would be settled in silence. A name
    outside TRACKED_ATTRS reads the same way and stands last, in sorted
    order.

    A str raises rather than being iterated. ConflictRow.attrs is the
    comma-joined string of exactly these names, so a caller reaching for
    it in place of the list is a live mistake, and a str's characters are
    none of those names: it would answer ((), ()) - no editorial half at
    all - and invert the decision made on the answer.
    """
    if isinstance(attrs, str):
        raise TypeError(
            "split_by_tier takes an iterable of attribute names, not the "
            f"comma-joined string {attrs!r}"
        )
    given = set(attrs)
    editorial = tuple(a for a in TRACKED_ATTRS if a in given and a not in MEASURED_ATTRS)
    unknown = tuple(sorted(given - set(TRACKED_ATTRS)))
    return editorial + unknown, tuple(a for a in MEASURED_ATTRS if a in given)


def unreadable_measured(values_by_attr) -> tuple[str, ...]:
    """The measured attribute names in values_by_attr whose values hold
    no readable disagreement, in MEASURED_ATTRS order.

    values_by_attr maps a measured attribute name to the values the
    group's members hold for it. A name answers here when it holds fewer
    than two values, or when any one of them spells no finite number: the
    empty string a record with no INFO element carries, a NaN, an
    infinity.

    Such a name is not two measurements disagreeing. It is one
    measurement and one absence, and the reasoning that settles a
    measured divergence - Traktor analysed the one file twice, so both
    numbers are real - says nothing about it. The caller fails closed on
    this answer: the group is a conflict the operator answers rather than
    a group settled by rule, which is the difference between keeping the
    record that holds no numbers and asking which record to keep
    (DL-325).
    """
    unreadable = []
    for attr in MEASURED_ATTRS:
        if attr not in values_by_attr:
            continue
        values = tuple(values_by_attr[attr] or ())
        if len(values) < 2 or any(measured_number(raw) is None for raw in values):
            unreadable.append(attr)
    return tuple(unreadable)


def outlier_attrs(values_by_attr, kept_by_attr) -> tuple[OutlierReading, ...]:
    """One reading per measured attribute in values_by_attr whose gap
    against the kept value exceeds OUTLIER_BAND of the larger of the two,
    in MEASURED_ATTRS order.

    values_by_attr maps a measured attribute name to the values the
    group's members hold for it; kept_by_attr maps it to the value the
    winning record holds - the number the merged collection will carry.
    The reading is taken from the kept value outwards, against the member
    value furthest from it, so the two numbers a reading names are the
    one the output holds and the one it does not. A spread read across
    all the members instead would, for a group of three, name two values
    the output holds neither of, under a row saying the output carries
    the record named beside it.

    A value that spells no finite number contributes nothing rather than
    raising: a record with no INFO element carries the empty string, and
    a page build is not the place a float() failure surfaces (the reason
    answer_detail.format_value returns None for the same input, ref:
    DL-248). An attribute whose kept value is one of those answers no
    reading at all - there is nothing for the gap to be read from. Such
    an attribute is named by unreadable_measured, and the caller has
    already made that group a conflict rather than asking for a reading
    on it.

    The comparison is against the LARGER value and is strict, so a gap
    exactly at the band is not an outlier: the band is where reading
    starts, not where it is reached. It is decided on exact rationals
    read from the decimal strings, so a gap exactly at the band is inside
    it whatever the attribute's spelling - 59.4 against 60.0 is exactly
    1% and divides to 0.010000000000000024 in floats. relative_gap stays
    a float, which is what the CLI line and the screen print.

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
        kept_raw = kept_by_attr.get(attr)
        kept_number = measured_number(kept_raw)
        if kept_number is None:
            continue
        kept_exact = _exact(kept_raw, kept_number)
        widest = None
        for raw in values_by_attr.get(attr) or ():
            number = measured_number(raw)
            if number is None or number == kept_number:
                continue
            other_exact = _exact(raw, number)
            larger = max(kept_exact, other_exact)
            if larger <= 0:
                continue
            gap = abs(kept_exact - other_exact) / larger
            if widest is None or gap > widest[0]:
                widest = (gap, str(raw))
        if widest is None:
            continue
        gap, other_raw = widest
        if gap > _OUTLIER_BAND_EXACT:
            readings.append(OutlierReading(attr, str(kept_raw), other_raw, float(gap)))
    return tuple(readings)
